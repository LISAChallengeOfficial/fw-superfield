#!/usr/bin/env python
"""The run script."""
import logging
import os
from pathlib import Path
from typing import List, Tuple, Union

# import flywheel functions
from flywheel_gear_toolkit import GearToolkitContext

from app.command_line import exec_command
from app.findMatchedScans import find_files
from utils.niftiHeader import pixSize
from utils.demo import get_demo

# The gear is split up into 2 main components. The run.py file which is executed
# when the container runs. The run.py file then imports the rest of the gear as a
# module.

log = logging.getLogger(__name__)

def main(context: GearToolkitContext) -> None:
    """Parses config and runs."""

   # subject_label, session_label = get_demo()


    # Get pixel size from nifti header
    #pixdim = pixSize()

    # Main event
    command = "/flywheel/v0/SF.sh" 
    print(command)
    exec_command(
    command,
    shell=True,
    cont_output=True,
        )

# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":  # pragma: no cover
    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gear_context:

        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gear_context.init_logging()

        # Pass the gear context into main function defined above.
        main(gear_context)
