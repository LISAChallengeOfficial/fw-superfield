#!/bin/bash
# 
# Run script for flywheel/Superfield.
#
# Authorship: Di Fan
#
##############################################################################

# Define directory names and containers
#source $FSLDIR/etc/fslconf/fsl.sh
FLYWHEEL_BASE=/flywheel/v0
INPUT_DIR=$FLYWHEEL_BASE/input
CONTAINER='[flywheel/hyperfine-ciso]'
work=/flywheel/v0/work
ANTSPATH='/opt/ants/bin/'
inputPath=/flywheel/v0/work/input
outputPath=/flywheel/v0/output

mkdir -p ${work}
mkdir -p ${inputPath}
mkdir -p ${outputPath}

sub=${1}
ses=${2}

##############################################################################

# Check for required files
# Parse configuration
function parse_config {

  CONFIG_FILE=$FLYWHEEL_BASE/config.json
  MANIFEST_FILE=$FLYWHEEL_BASE/manifest.json

  if [[ -f $CONFIG_FILE ]]; then
    echo "$(cat $CONFIG_FILE | jq -r '.config.'$1)"
  else
    CONFIG_FILE=$MANIFEST_FILE
    echo "$(cat $MANIFEST_FILE | jq -r '.config.'$1'.default')"
  fi
}
 
# define app options
imageDimension="$(parse_config 'imageDimension')" 
Iteration="$(parse_config 'Iteration')" 
transformationModel="$(parse_config 'transformationModel')"   
similarityMetric="$(parse_config 'similarityMetric')"  
target_template="$(parse_config 'target_template')"    
prefix="$(parse_config 'prefix')" 
phantom="$(parse_config 'phantom')" 

##############################################################################
# Handle INPUT file

# Find input file In input directory with the extension
# .zip

echo "work directory contents:"
echo "$(ls -l $work)"
nvidia-smi

zip_file=`find $INPUT_DIR -type f -iname '*.zip'`
echo $zip_file
unzip -j "$zip_file" -d "$inputPath"

python FlyWheelScript.py --input_folder "$inputPath" --output_folder "$outputPath"





