#!/bin/bash

# declare an array called array and define 3 vales
experiments=(
# ONOS
#  "TEST_ONOS_NO_SMOTE_ORVM00"
#  "TEST_ONOS_NO_SMOTE_ORVM01"
#  "TEST_ONOS_NO_SMOTE_ORVM01_2"
#  "TEST_ONOS_NO_SMOTE_ORVM01_3"
#  "TEST_ONOS_NO_SMOTE_ORVM02"
#  "TEST_ONOS_NO_SMOTE_ORVM02_2"
#  "TEST_ONOS_NO_SMOTE_ORVM03"
#  "TEST_ONOS_NO_SMOTE_ORVM03_2"
#  "TEST_ONOS_NO_SMOTE_ORVM04"
#  "TEST_ONOS_NO_SMOTE_ORVM04_2"
# BEADS
  "TEST_ONOS_BEADS_ORVM02"
  "TEST_ONOS_BEADS_ORVM03"
  "TEST_ONOS_BEADS_ORVM04"
  "TEST_ONOS_BEADS_ORVM05"
)

test_dataset=(
  "/Users/raphael.ollando/OneDrive - University of Luxembourg/04_Papers/00_FIGSDN/00_experiments/01_RQ1/00_test_data/ONOS_UNKNOWN_REASON_3_METHODS_15000.arff"
  "/Users/raphael.ollando/OneDrive - University of Luxembourg/04_Papers/00_FIGSDN/00_experiments/01_RQ1/00_test_data/ONOS_UNKNOWN_REASON_FIGSDN_5000.arff"
  "/Users/raphael.ollando/OneDrive - University of Luxembourg/04_Papers/00_FIGSDN/00_experiments/01_RQ1/00_test_data/ONOS_UNKNOWN_REASON_BEADS_5000.arff"
  "/Users/raphael.ollando/OneDrive - University of Luxembourg/04_Papers/00_FIGSDN/00_experiments/01_RQ1/00_test_data/ONOS_UNKNOWN_REASON_DELTA_5000.arff"
)
for expt in "${experiments[@]}" ; do
  for test_data in "${test_dataset[@]}"; do
    echo "Reporting on experiment ${expt} with ${test_data}"
    figsdn experiment report "${expt}" --no-download --test-on-data "${test_data}"
  done
done

# Command available only on mac
osascript -e 'tell app "System Events" to display notification "Done reporting experiments"'