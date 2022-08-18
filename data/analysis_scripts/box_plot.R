

# Import the data and look at the first six rows
data <- read.csv(file='/Users/raphael.ollando/Library/Application Support/figsdn/report/TEST_ONOS_NO_SMOTE_ORVM01/results.csv')
data[is.na(data)] <- 0
head(data)

x <- data$iteration
y <- data$learning_precision

plot(
  x,y,
  xlab = "# of iteration",
  ylab = "precision",
  main = "Precision per iteration",
  type = "b",
  pch = 3
)