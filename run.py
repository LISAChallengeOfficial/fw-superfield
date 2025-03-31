#!/usr/bin/env python
"""The run script."""
import logging
import os
from datetime import datetime

# import flywheel functions
from flywheel_gear_toolkit import GearToolkitContext
import flywheel

# import custom functions
from utils.parser import parse_config
from utils.parser import download_dataset
from app.main import fw_process_subject
import utils.bids as gb


# The gear is split up into 2 main components. The run.py file which is executed
# when the container runs. The run.py file then imports the rest of the gear as a
# module.

log = logging.getLogger(__name__)

def main(context: GearToolkitContext) -> None:
    """Parses config and runs."""
    # Initialize Flywheel context and configuration
    context = flywheel.GearContext()
    config = context.config
    input_container, config, manifest = parse_config(context)

    # Download the dataset 
    print('Step 2: Downloading dataset')
    subses = download_dataset(context, input_container, config)
    print(f"subses: {subses}")

    # Process each subject and create a new analysis container for each
    print('Step 4: Processing each subject')
    for sub in subses.keys():
            for ses in subses[sub].keys():
                print(f"Processing subject {sub} session {ses}")
                raw_fnames, deriv_fnames, logs = fw_process_subject(sub, ses, config)
        
                # Check for missing input or output
                if not raw_fnames:
                    gb._logprint(f"[SKIPPING] No input files for {sub}/{ses}.")
                    continue
                if not deriv_fnames:
                    gb._logprint(f"[ERROR] Processing failed for {sub}/{ses}: No derived output.")
                    # Delete files in raw_fnames because derived output is missing
                    for file_path in raw_fnames:
                        try:
                            os.remove(file_path)
                            gb._logprint(f"Deleted raw file: {file_path}")
                        except Exception as e:
                            gb._logprint(f"Error deleting {file_path}: {e}")
                    continue

                out_files = []
                out_files.extend(raw_fnames)
                out_files.extend(deriv_fnames)
                out_files.extend(logs)

                # # Create a new analysis
                # gversion = manifest["version"]
                # gname = manifest["name"]
                # gdate = datetime.now().strftime("%Y%M%d_%H:%M:%S")
                # image = manifest["custom"]["gear-builder"]["image"]
                # session_container = context.client.get(subses[sub][ses])
                
                # analysis = session_container.add_analysis(label=f'{gname}/{gversion} {gdate}')
                # analysis.update_info({"gear":gname,
                #                     "version":gversion, 
                #                     "image":image,
                #                     "Date":gdate,
                #                     "status": "failed" if not deriv_fnames else "success",
                #                     "note": "No derived outputs, processing may have failed." if not deriv_fnames else "",
                #                     **config})

                # for file in out_files:
                #     gb._logprint(f"Uploading output file: {os.path.basename(file)}")
                #     analysis.upload_output(file)


# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":  # pragma: no cover
    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gear_context:

        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gear_context.init_logging()

        # Pass the gear context into main function defined above.
        main(gear_context)
