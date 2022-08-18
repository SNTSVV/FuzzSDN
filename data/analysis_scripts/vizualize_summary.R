# ------------
# Introduction
# ------------

NAME <- 'start_template_R' ## Name of the R file goes here (without the file extension!)
PROJECT <- 'test'

# ------------
# Preamble
# ------------

## -------
## Imports
## -------
library("xtable")

## --------
## Settings
## --------

# Location of the report directory for FIGSDN
REPORT_DIR <- paste(path.expand('~'), 'Library/Application Support/figsdn/report/', sep='/')
SUMMARY_PATH <- paste0(REPORT_DIR, "summary.csv")
IT_TO_DISPLAY <- list(0, 20, 40)
# ---------
# Main code
# ---------
summary_data <- read.csv(file = SUMMARY_PATH, sep = ',')


tbl <- ftable(summary_data)
print.xtableFtable(tbl)