"""Parser module to parse gear config.json."""

from typing import Tuple
from flywheel_gear_toolkit import GearToolkitContext
import argparse
import os
import json
import subprocess
import logging
import warnings
import flywheel
from utils.bids import import_dicom_folder, setup_bids_directories
import datetime
import re
from string import ascii_lowercase as alc
from pathlib import Path

def parse_config(context):
    """Parse the config and other options from the context, both gear and app options.

    Returns:
        file output label
        model name
    """

    # GPU status
    # subprocess.run(["nvidia-smi"], check=True)
    
    base_dir = '/flywheel/v0'
    input_dir = base_dir + '/input/'
    work_dir = base_dir + '/work/'
    output_dir = base_dir + '/output/'
    # Get the input file id
    input_container = context.client.get_analysis(context.destination["id"])
    
    input_id = '64834ac0807af4cddffe5e2f' #input_container.parent.id
    container = context.client.get(input_id)
    print(f"Container type: {container.container_type}")
    print(f"Container label: {container.label}")
    print(f"Container ID: {container.id}")

    # Read config.json file
    with open(base_dir + '/config.json') as f:
        config = json.load(f)
    
    # Read manifest.json file
    with open(base_dir + '/manifest.json') as f:
        manifest = json.load(f)

    config = config['config']
    config['input_dir'] = input_dir
    config['work_dir'] = work_dir
    config['output_dir'] = output_dir
    config['bids_config_file'] = base_dir + '/utils/dcm2bids_config.json'
    return container, config, manifest


def download_dataset(gear_context: GearToolkitContext, container, config):
    
    work_dir = config['work_dir']
    # force_run = config['force_run']
    force_run = True

    setup_bids_directories(work_dir)
    # import_options = {'config': config['bids_config_file'], 'projdir': work_dir, 'skip_dcm2niix': True}

    source_data_dir = os.path.join(work_dir, 'sourcedata')
    os.makedirs(source_data_dir, exist_ok=True)
    
    input_gear = config['input_gear']
    print(f"Input gear: {input_gear}")

    print(f"Downloading {container.label}...")
    print(f"Container type: {container.container_type}" )

    if container.container_type == 'project':
        proj_label, subjects = download_project(container, source_data_dir, force_run, input_gear, dry_run=False)
        print(f"Downlaoded project data, moving on to making BIDS structure...")

        output = {}
        for sub in subjects.keys():
            output[sub] = {}
            sessions = subjects[sub]

            for ses in sessions.keys():
                print(f"Importing {sub} {ses}...")
                # import_dicom_folder(dicom_dir=subjects[sub][ses]['folder'], sub_name=sub, ses_name=ses, **import_options)
                output[sub][ses] = subjects[sub][ses]['id']

        return output

    elif container.container_type == 'subject':
        proj_label = gear_context.client.get(container.parents.project).label
        source_data_dir = os.path.join(source_data_dir, proj_label)
        
        sub_label, sessions = download_subject(container, source_data_dir, force_run, dry_run=False)
        
        output = {sub_label:{}}

        for ses in sessions.keys():
            # import_dicom_folder(dicom_dir=sessions[ses]['folder'], sub_name=sub_label, ses_name=ses, **import_options)
            output[sub_label][ses] = sessions[ses]['id']
        
        return output

    elif container.container_type == 'session':
        proj_label = gear_context.client.get(container.parents.project).label
        sub_label = make_subject_label(gear_context.client.get(container.parents.subject))
        source_data_dir = os.path.join(source_data_dir, proj_label, sub_label)
        
        ses_label, ses_dir, ses_id = download_session(container, source_data_dir, force_run, dry_run=False)
        # import_dicom_folder(dicom_dir=ses_dir, sub_name=sub_label, ses_name=ses_label, **import_options)

        return {sub_label: {ses_label: ses_id}}


def make_session_label(ses) -> str:
    return ses.label.split()[0].replace("-",'').replace("_", "")

# Forcing BIDS compliance by removing spaces and dashes in subject labels
def make_subject_label(sub) -> str:
    return sub.label.replace("-", '').replace(" ", '').replace("_", "") 

def make_project_label(proj) -> str:
    return proj.replace("-", '_').replace(" ", '')

def download_file(
    ses_container,
    output_dir,
    input_gear="mrr",
):
    """
    Download all files under acquisitions of an analysis container.

    Args:
        ses_container: Flywheel session container
        output_dir (Path or str): where to save files
        dry_run (bool): if True, don’t actually download
        analysis_container: (optional) explicit analysis Container object
        analysis_label (str): label of the analysis to use if container isn’t provided
    """
    print(f"Downloading files for session {ses_container.label}...")


    latest_analysis = None
    latest_time = None
    ses_container = ses_container.reload()
    # Loop over analyses in the session container
    for analysis in ses_container.analyses:
        analysis = analysis.reload()

        try:
            # Check that the analysis exists and has gear_info and job info
            if analysis is None:
                continue
            # Make sure gear_info is not None before accessing its name
            if not analysis.gear_info or not analysis.gear_info.name:
                continue

            # Filter by gear name and job state complete
            if input_gear in analysis.gear_info.name:
                print(f"input_gear analysis: {analysis.gear_info.name}")
                job = analysis.get("job")
                if job is None or job.get("state") != "complete":
                    continue

                analysis_time = analysis.created 

                # Update latest_analysis if this one is newer
                if latest_time is None or analysis_time > latest_time:
                    latest_time = analysis_time
                    latest_analysis = analysis

        except AttributeError as e:
            # Handle cases where expected attributes are missing
            print(f"Skipping analysis due to missing attribute: {e}")
            continue

    if latest_analysis:

        # Download matching files from the latest analysis
        for analysis_file in latest_analysis.files:
            # Check that file has type and name attributes
            try:
                if analysis_file.type == "nifti" and "mrr-axireg" in analysis_file.name:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        download_path = os.path.join(output_dir, analysis_file.name)
                        analysis_file.download(download_path)
                        print(f"Downloaded file: {analysis_file.name}")
                    except Exception as e:
                        print(f"Error downloading {analysis_file.name}: {e}")
            except AttributeError as e:
                print(f"Skipping file due to missing attribute: {e}")
    else:
        print("No matching analysis found.")
        exit(1)




    # ses_container = ses_container.reload()
    # for analysis in ses_container.analyses:
    #     # and analysis.gear_info.version == '0.1.3' 
    #     if analysis and input_gear in analysis.gear_info.name and analysis.get("job").get("state") == "complete":
    #         print(f"analysis.label: {analysis.label}")
    #         print(f"analysis.gear_info.name: {analysis.gear_info.name}")

    #         for analysis_file in analysis.files:
    #             if analysis_file.type == "nifti" and "mrr-axireg" in analysis_file.name:
    #                 try:
    #                     file = analysis_file
    #                     os.makedirs(output_dir, exist_ok=True)
    #                     download_dir = os.path.join(output_dir, file.name)
    #                     file.download(download_dir)
    #                     print(f"Downloaded file: {file.name}")
                        
    #                 except Exception as e:
    #                     print(f"Error downloading {file.name}: {e}")


def download_session(ses_container, sub_dir, force_run, input_gear, dry_run=False) -> Tuple[str, str]:
    print("--- Downloading session ---")
    print(f"Session label: {ses_container.label}")
    # print(f"Acquisitions: {len(ses_container.acquisitions())}")
    print(f"force_run: {force_run}")

    ses_label = make_session_label(ses_container)
    ses_dir = os.path.join(sub_dir, ses_label)
    ses_id = ses_container.id

    proceed = True
    # if force_run:
    #     print(f"[FORCE RUN] Skipping age check and saving data into: {ses_dir}")
    #     proceed = True
    #     age = "unknown"  # Optional, if you still want to log age
    # else:
    #     age_check, age = check_age(ses_id)
    #     if not age_check:
    #         print(f"Age {age} is not within the model range 3 months - 3 years")
    #         proceed = False
    #     else:
    #         print(f"Saving data into: {ses_dir}")
    #         proceed = True

    if proceed:
        download_file(ses_container, ses_dir, input_gear)

    return ses_label, ses_dir, ses_id


def download_subject(sub_container, proj_dir, force_run, input_gear, dry_run=False):
    print("--- Downloading subject ---")
    print(f"Label: {sub_container.label}")
    print(f"Sessions: {len(sub_container.sessions())}")
    
    sub_label = make_subject_label(sub_container)
    sub_dir = os.path.join(proj_dir, sub_label)
    # print(f"Saving data into: {sub_dir}")
    
    sessions_out = {}

    for ses in sub_container.sessions.iter():
        ses_label0, ses_dir, ses_id = download_session(ses, sub_dir, force_run, input_gear, dry_run=dry_run)

        # Check for duplicate session labels
        ses_label = ses_label0; i = 0
        
        while ses_label in sessions_out:
            ses_label = ses_label0 + alc[i]
            i += 1
        

        sessions_out[ses_label] = {'folder':ses_dir, 'id':ses_id}

    return sub_label, sessions_out


def download_project(project, my_dir, force_run, input_gear, dry_run=False):
    print("--- Downloading project ---")
    print(f"Label: {project.label}")
    print(f"Subjects: {project.stats.number_of.subjects}")
    print(f"Sessions: {project.stats.number_of.sessions}")
    # print(f"Acquisitions: {project.stats.number_of.acquisitions}")
    
    proj_name = make_project_label(project.label)
    # my_dir = os.path.join(my_dir, proj_name)
    # print(f"Saving data into: {my_dir}")
    
    subjects_out = {}
    for sub in project.subjects.iter():
        sub_lab, sessions_dict = download_subject(sub, my_dir, force_run, input_gear, dry_run=dry_run)
        subjects_out[sub_lab] = sessions_dict

    return proj_name, subjects_out



def parse_arguments(sub, ses):

    parser = argparse.ArgumentParser(
        # description=description,
        formatter_class=argparse.RawTextHelpFormatter
    )

    print(f"Sub: {sub}")
    print(f"Ses: {ses}")

    in_dir = Path(f"/flywheel/v0/work/sourcedata/{sub}/{ses}/")
    raw_fnames = os.listdir(in_dir)
    output_path = Path(f"/flywheel/v0/work/derivatives/sub-{sub}/ses-{ses}/")
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Input folder: {in_dir}")
    print(f"Output folder: {output_path}")

    parser.add_argument('--spacing', type=float, nargs=3, default=[1.0, 1.0, 1.0],
                        help='Target spacing for resampling (default: 1.0, 1.0, 1.0)')
    parser.add_argument('--intensity_upper', type=int, default=3000,
                        help='Upper limit for intensity scaling (default: 3000)')
    parser.add_argument('--input_folder', type=str, default=in_dir,
                        help='Path to the input folder containing .nii.gz images')
    parser.add_argument('--output_folder', type=str, default=output_path,
                        help='Path to the output folder for processed images')
    parser.add_argument('--sw_overlap', type=float, default=0.9,
                        help='Sliding window overlap for inference (default: 0.9)')
    parser.add_argument('--sw_batch_size', type=int, default=8,
                        help='Sliding window batch size (default: 8)')
    if '--help' in os.sys.argv or '-h' in os.sys.argv:
        print("\n\nExample usage:\n\n"
              "python script.py --input_folder /path/to/input --output_folder /path/to/output "
              "--spacing 1.0 1.0 1.0 --intensity_upper 2500 --sw_overlap 0.8")
    return parser.parse_args(), raw_fnames


# def check_age(ses_id):
#     """Check if the age is within the model range 3months - 3 years"""
#     # check custom fields for age, then check Age field, then check dicom headers
#     context = flywheel.GearContext()
#     ses = context.client.get(ses_id)

#     # Read config.json file
#     p = open('/flywheel/v0/config.json')
#     config = json.loads(p.read())
#     # Read API key in config file
#     api_key = (config['inputs']['api-key']['key'])
#     fw = flywheel.Client(api_key=api_key)

#     print(f"Checking age in session demographic sync...")
#     age_in_months = 0
#     if 'age_at_scan_months' in ses.info and ses.info['age_at_scan_months'] not in (0, None): 
#         age_in_months = ses.info['age_at_scan_months']
#         print(f"Age in months in session demographic sync: {age_in_months}")
#     else:
#         print("No age in session demographic sync...")
#         print("Checking age in dicom header...")
#         for acq in ses.acquisitions.iter():
#             acq = acq.reload()
#             if 'T2' in acq.label and 'AXI' in acq.label and 'Segmentation' not in acq.label and 'Align' not in acq.label: 
#                 for file_obj in acq.files: # get the files in the acquisition
#                     # Screen file object information & download the desired file
#                     if file_obj['type'] == 'dicom':
#                         dicom_header = fw._fw.get_acquisition_file_info(acq.id, file_obj.name)
#                         print(f"Acquisition label: {acq.label}")
#                         if 'PatientBirthDate' in dicom_header.info:
#                             print("Checking DOB in dicom header...")
#                             try:
#                                 dob = dicom_header.info['PatientBirthDate']
#                                 seriesDate = dicom_header.info['SeriesDate']
#                                 # Validate date format and presence of SeriesDate
#                                 if not seriesDate:
#                                     raise ValueError("SeriesDate is missing")
                                    
#                                 # Calculate age at scan
#                                 age = (datetime.strptime(seriesDate, '%Y%m%d')) - (datetime.strptime(dob, '%Y%m%d'))
#                                 age_in_days = age.days
#                                 age_in_months = int(age_in_days / 30.44)
#                                 print(f"Age in months in dicom header: {age_in_months}")

#                                 # Sanity check for negative ages or unreasonable values
#                                 if age_in_days < 0:
#                                     raise ValueError(f"Invalid age calculation: {age_in_days} days")
                                        
#                             except ValueError as e:
#                                 print(f"Error processing dates: {e}")
#                                 raise

#                         elif 'PatientAge' in dicom_header.info:
#                             print("No DOB in dicom header or age in session info! Trying PatientAge from dicom...")
#                             try:
#                                 age = dicom_header.info['PatientAge']
#                                 if not age:
#                                     raise ValueError("PatientAge is empty")
                                    
#                                 if age.endswith('M'):
#                                     # Remove leading zeros and 'M', then convert to int
#                                     age_in_months = int(age.rstrip('M').lstrip('0'))
#                                     if age_in_months == 0:
#                                         raise ValueError("Age cannot be 0 months")
#                                     age_in_days = int(age_in_months * 30.44)
#                                 else:
#                                     # Original case for days ('D')
#                                     age = re.sub('\D', '', age)
#                                     age_in_days = int(age)
#                                     age_in_months = int(age_in_days / 30.44)
                                    
#                                 # Sanity check
#                                 if age_in_days < 0 or age_in_days > 36500:
#                                     raise ValueError(f"Unreasonable age value: {age_in_days} days")
                                    
#                             except (ValueError, TypeError) as e:
#                                 print(f"Error processing DICOM age: {e}")
#                                 raise
#                         else:
#                             print("No age at scan in session info label! Ask PI...")
#                             raise ValueError("No valid age information found")
        
#     # accept age in months between 1 and 42 months (3.5 years)
#     if age_in_months > 1 and age_in_months < 42:
#         return True, age_in_months
#     else:
#         return False, age_in_months
