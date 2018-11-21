Program log-splitter/main.py is a program that:
 * reads qpid-dispatch log files
 * filters out everything except AMQP log traces
 * sorts the log traces by AMQP connection
 * produces a high level summary of the busiest connections
 * identifies probably interrouter connections
 * produces a statistics page that shows for each connection:
   * number of log lines
   * number of AMQP transfer log lines

The log AMQP data is rewritten into per-connection files. In the case this
was developed to solve the data rewrite is equivalent to doing 42,000 greps
and saving the result into individual files. The output files are saved
in a folder named after the original log file and then in subfolders
indicating how many log lines the files hold.

  Log file  : big.log
  Storage   : big.log.splits/
  Data dirs : big.log.splits/10e1, big.log.splits/10e2, ...

The resulting data files may then be used as input to other tools such as
adverbl.
