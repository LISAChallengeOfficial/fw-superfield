import os
import glob
import argparse
import time
import warnings
import torch
import numpy as np
import SimpleITK as sitk

from monai import transforms
from monai.data import list_data_collate, decollate_batch
from monai.inferers import sliding_window_inference
from monai.networks.nets import SwinUNETR
from functools import partial

warnings.filterwarnings("ignore")
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  # Disable oneDNN custom operations

description = (
    "\n\n***********************************"
    "\nSuper-Field enhancment of ultra-low field images with SFNet. Utility patent pending. "
    "\nNot for use or distribution outside the use of the Gates/UNITY project. "
    "\nFor questions, please contact Austin Tapp at atapp@childrensnational.org. "
    "\n\nIf you use this algorithm for any of your work, please ensure it is cited as follows:\n\n"
    "Tapp, A. et al. (2024). Super-Field MRI Synthesis for Infant Brains Enhanced by Dual Channel Latent Diffusion. "
    "In: Linguraru, M.G., et al. Medical Image Computing and Computer Assisted Intervention – MICCAI 2024. "
    "MICCAI 2024. Lecture Notes in Computer Science, vol 15003. Springer, Cham. "
    "https://doi.org/10.1007/978-3-031-72384-1_42"
    "\n\n***********************************"
)

print(description)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--spacing', type=float, nargs=3, default=[1.0, 1.0, 1.0],
                        help='Target spacing for resampling (default: 1.0, 1.0, 1.0)')
    parser.add_argument('--intensity_upper', type=int, default=3000,
                        help='Upper limit for intensity scaling (default: 3000)')
    parser.add_argument('--input_folder', type=str, required=True,
                        help='Path to the input folder containing .nii.gz images')
    parser.add_argument('--output_folder', type=str, required=True,
                        help='Path to the output folder for processed images')
    parser.add_argument('--sw_overlap', type=float, default=0.9,
                        help='Sliding window overlap for inference (default: 0.9)')
    parser.add_argument('--sw_batch_size', type=int, default=8,
                        help='Sliding window batch size (default: 8)')
    if '--help' in os.sys.argv or '-h' in os.sys.argv:
        print("\n\nExample usage:\n\n"
              "python script.py --input_folder /path/to/input --output_folder /path/to/output "
              "--spacing 1.0 1.0 1.0 --intensity_upper 2500 --sw_overlap 0.8")
    return parser.parse_args()


def resample_to_spacing(uLF, spacing):
    target_spacing = spacing

    uLF_size = uLF.GetSize()
    uLF_spacing = uLF.GetSpacing()
    uLF_extent = [sz * sp for sz, sp in zip(uLF_size, uLF_spacing)]

    new_size = [int(round(ext / ts)) for ext, ts in zip(uLF_extent, target_spacing)]

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing(target_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputOrigin(uLF.GetOrigin())
    resampler.SetOutputDirection(uLF.GetDirection())
    resampler.SetInterpolator(sitk.sitkLanczosWindowedSinc)

    uLF_resampled = resampler.Execute(uLF)
    return uLF_resampled


def rescale(SF, max):
    GT_min, GT_max = 0, max
    SF_min, SF_max = np.min(SF), np.max(SF)
    target_range = GT_max - GT_min
    SF_range = SF_max - SF_min
    scale_factor = target_range / SF_range
    SFrescale = (SF - SF_min) * scale_factor + GT_min
    return SFrescale


if __name__ == "__main__":
    args = parse_arguments()

    input_folder = os.path.abspath(args.input_folder)
    output_folder = os.path.abspath(args.output_folder)
    spacing = args.spacing
    intensity_upper = args.intensity_upper
    sw_overlap = args.sw_overlap
    sw_bs = args.sw_batch_size

    model_path = os.path.join("SF_model.pt")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    input_images = sorted(glob.glob(os.path.join(input_folder, "*.nii.gz")))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = SwinUNETR(img_size=(96, 96, 96), in_channels=1, out_channels=1, feature_size=48, use_v2=True)
    model.load_state_dict(torch.load(model_path)['state_dict'])
    model.to(device)
    model.eval()

    inferer = partial(sliding_window_inference, roi_size=(96, 96, 96), sw_batch_size=sw_bs, predictor=model,
                      overlap=sw_overlap)

    transform_pipeline = transforms.Compose([
        transforms.LoadImaged(keys=["image"]),
        transforms.EnsureChannelFirstd(keys=["image"]),
        transforms.EnsureTyped(keys=["image"]),
        transforms.SpatialPadd(keys=["image"], spatial_size=(96, 96, 96), mode='empty'),
        transforms.ScaleIntensityRangePercentilesd(keys=["image"], lower=0, upper=99.5, b_min=0, b_max=1),
    ])

    for img_path in input_images:
        img_name = os.path.basename(img_path).split(".")[0]
        image_data = {"image": img_path}
        batch_data = transform_pipeline(image_data)
        batch_data = list_data_collate([batch_data])
        img_tensor = batch_data['image'].to(device)

        img_tensor.applied_operations = batch_data['image'].applied_operations
        batch_data.update({'image': img_tensor})
        batch_data = [transform_pipeline.inverse(i) for i in decollate_batch(batch_data)]

        LF = batch_data[0]["image"]
        LF_PP = LF[0].detach().cpu().numpy().astype(np.float32)
        LF_PP = np.swapaxes(LF_PP, 0, 2)
        LF_PP = sitk.GetImageFromArray(LF_PP)

        original = sitk.ReadImage(img_path)
        LF_PP.SetOrigin(original.GetOrigin())
        LF_PP.SetDirection(original.GetDirection())
        LF_PP.SetSpacing(original.GetSpacing())

        LF_PP = resample_to_spacing(LF_PP, spacing)
        LF_PP.SetOrigin(original.GetOrigin())
        LF_PP.SetDirection(original.GetDirection())

        pp_img_path = os.path.join(output_folder, f"{img_name}_PP.nii.gz")
        sitk.WriteImage(LF_PP, pp_img_path)
        time.sleep(5)

        pp_image_data = {"image": pp_img_path}
        pp_batch_data = transform_pipeline(pp_image_data)
        pp_batch_data = list_data_collate([pp_batch_data])
        pp_img_tensor = pp_batch_data['image'].to(device)

        with torch.no_grad():
            prediction = inferer(pp_img_tensor)
            prediction.applied_operations = pp_batch_data['image'].applied_operations
            pp_batch_data.update({'image': prediction})
            pp_batch_data = [transform_pipeline.inverse(i) for i in decollate_batch(pp_batch_data)]
            prediction = pp_batch_data[0]["image"]
            prediction = prediction[0].detach().cpu().numpy().astype(np.float32)
            prediction = np.swapaxes(prediction, 0, 2)
            prediction = rescale(prediction, intensity_upper)
            output_image = sitk.GetImageFromArray(prediction)

        output_image.SetOrigin(original.GetOrigin())
        output_image.SetDirection(original.GetDirection())

        output_path = os.path.join(output_folder, f"{img_name}_SF.nii.gz")
        sitk.WriteImage(output_image, output_path)
        os.remove(pp_img_path)
        print(f"Saved: {output_path}")

    print("Super-field processing complete!")
