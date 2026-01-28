* Execute Stata do file then exit, putting log file in subdirectory ./logs.
* Input do file can be passed either as "filename" or "filename.do", and
* log file will be "output/logs/filename.log".
*
* Note that running
*
* stata execute file.do
*
* at a command prompt is similar to using batch mode,
*
* stata -b file.do
*
* but allows control over the location of the log file (in batch mode,
* Stata always creates a log file in the current directory).   

program execute

   quietly capture log close
   local doFile `1'

   * Create logs directory if it doesn't exist
   capture mkdir output
   capture mkdir output/logs
   
   * Extract just the filename without directory path
   * Find the last "/" or "\\" and extract everything after it
   local baseFile "`doFile'"
   local lastSlash = 0
   forvalues i = 1/`=length("`doFile'")' {
      if substr("`doFile'", `i', 1) == "/" | substr("`doFile'", `i', 1) == "\\\\" {
         local lastSlash = `i'
      }
   }
   if `lastSlash' > 0 {
      local baseFile = substr("`doFile'", `lastSlash' + 1, .)
   }
   
   * Create name of log file from base filename
   local doLocation = strpos("`baseFile'", ".do")
   if "`doLocation'" == "0" {
      local logFile "`baseFile'.log" // If name does not contain ".do", just append ".log"
      }
   else { // If it does, replace ".do" with ".log"
      local logFile = substr("`baseFile'", 1, `doLocation')
      local logFile = "`logFile'log"
      }   

   * Start logging
   quietly log using output/logs/`logFile', replace text

   * Execute command line with error handling
   * - capture: Prevents error from stopping execution
   * - noisily: Shows error messages to user
   capture noisily do `*'
   local rc = _rc

   * Turn off logging and exit Stata
   quietly log close
   
   * Exit with appropriate return code
   * - If error occurred (rc != 0), exit with that code to propagate failure
   * - Otherwise, exit cleanly with STATA keyword to force exit
   if `rc' != 0 {
      display as error "Error in do-file (return code: `rc')"
      exit `rc'
   }
   exit, clear STATA

end
