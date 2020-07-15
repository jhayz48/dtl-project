import os
import sys
import ConfigParser
import logging
import logging.handlers
import argparse
import time
import urllib2
import datetime

config = ConfigParser.ConfigParser()
cache = ConfigParser.RawConfigParser()
logger  = logging.getLogger(__name__)

if len(sys.argv) > 1:
	config_file = sys.argv[1]

def init_global():
	global _start_date
	global _start_seq
	global _end_date
	global _end_seq
	global _all
	
	_start_date = ""
	_start_seq = ""
	_end_date = ""
	_end_seq = ""
	_all = ""
	
def download_data(url, dir, file):
	logger.info("downloading file (%s) from url: [%s]", file, url)
	logger.debug("url: [%s]", url)
	logger.debug("dir: [%s]", dir)
	logger.debug("file: [%s]", file)
	
	r = urllib2.urlopen(url)	
	# download data
	data = r.read()
	# build filename
	filename = dir +"/"+ file	
	
	# write data to file
	try:
		with open(filename, 'wb') as f:
			f.write(data)
		print "file downloaded [" +file+"]"
	except Exception, e:
		logger.error("failed to write data (%s)", e)
		print "Failed to write data" + str(e)


def download_date(seq, date):
	logger.debug("downloading data for date: [%s : %d]", date, seq)
	
	# get date string for replace
	date_str = config.get('DEFAULT','DATE_STR')
	
	# iterate all data to download
	
	for x in config.get('DATA','sections').split(','):
		section_name = x.strip()
		logger.debug("[%s]", section_name)
		url = config.get(section_name,'url')
		dir = config.get(section_name,'out_dir')
		file = config.get(section_name,'out_file')
		
		download_data(url.replace(date_str,str(seq)), dir, file.replace(date_str,date))

		
def find_date():

	global _start_date
	global _start_seq
	global _end_date
	global _end_seq

	start_seq = ""
	start_date = ""
	
	count = 0
	
	print "checking last downloaded date in cache"
	logger.info("checking last downloaded date in cache")
	max = config.getint('CONFIG','max_seq')
	
	# find last date in cache
	for x in range(0, max):
		date = datetime.date.today()-datetime.timedelta(x)
		date = date.strftime('%Y%m%d')
		#print "Checking date: " + date 
		logger.debug("checking date: [%s]", date) 
		# check if date ex
		if (cache.has_option('DEFAULT', str(date))):			 
			start_seq = cache.get('DEFAULT', date)
			start_date = date
			logger.debug("found last downloaded date: [%s] = [%s] ", date, start_seq)
			count = x
			break
				
	#print "Found last downloaded is : " +_start_date + " = " +_start_seq
	logger.debug("found last downloaded is : %s = %s", _start_date, _start_seq)
	
	# if start date/seq not specified 
	if(len(_start_seq) == 0):
		print "start date is empty!" + _start_date
		logger.info("start date is empty: [%s]", _start_date)
		_start_seq = start_seq
		print "using date " +start_date+ " (" +start_seq+")"
		logger.info("using date %s (%s)", _start_date, _start_seq)

	_start_date = cache.get('DEFAULT', _start_seq)
	
	# if end date/seq not specified
	if(len(_end_seq) == 0):
		print "checking latest available download date"
		logger.info("checking latest available download date")
		
		# find seq of latest available date
		cache_file = config.get('CONFIG','cache_file')
		cache_url = config.get('CONFIG','cache_url')
		date_str = config.get('DEFAULT','date_str')
		max_days = config.getint('CONFIG','max_days') # max forward days to search
		sleep_time = config.getint('CONFIG','sleep_time')
		for x in range(int(start_seq), int(start_seq)+count+max_days):
			date = get_date(cache_url.replace(date_str,str(x)))
			logger.debug("%s = %s", date, str(x)) 
			#print date +" = "+ str(x)
			if(date != "YYYYMMDD"):
				cache.set('DEFAULT', date, str(x))	# lookup
				cache.set('DEFAULT', str(x), date)	# reverse lookup
				_end_seq = str(x)
				_end_date = date
			time.sleep(sleep_time)
		# write cache to file
		write_cache(cache_file)	
		
		# update max_seq in config
		config.set('CONFIG','max_seq',_end_seq)
		update_config(config_file)
		
		print "found latest is: " +_end_date+ " = " +_end_seq
		logger.info("found latest is : %s = %s", _end_date, _end_seq)
		
	_end_date = cache.get('DEFAULT', _end_seq)	

def get_next_date(date):

	try:
		date = datetime.datetime.strptime(date,'%Y%m%d')
	except Exception, e:
		logger.error("invalid date [%s]: (%s)", date, e)
		print "invalid date [" +date+ "]: " +str(e)
		return ""
		
	max_days = config.getint('CONFIG','max_days') # max days to search
	for x in range(1, max_days):
		day=date + datetime.timedelta(x) # get next day
		day=day.strftime('%Y%m%d')
		if(cache.has_option('DEFAULT',day)):
			return day
			
	# if not found return empty
	return ""

def get_prev_date(date):

	try:
		date = datetime.datetime.strptime(date,'%Y%m%d')
	except Exception, e:
		logger.error("invalid date [%s]: (%s)", date, e)
		print "invalid date [" +date+ "]: " +str(e)
		return ""
		
	max_days = config.getint('CONFIG','max_days') # max days to search
	for x in range(1, max_days):
		day=date - datetime.timedelta(x) # get previous day
		day=day.strftime('%Y%m%d')
		if(cache.has_option('DEFAULT',day)):
			return day
			
	# if not found return empty
	return ""	

def check_seq(seq):

	cache_file = config.get('CONFIG','cache_file')
	cache_url = config.get('CONFIG','cache_url')
	date_str = config.get('DEFAULT','date_str')

	logger.info("checking sequence if available for download: %s", seq)
	print "checking sequence if available for download: " +seq	
	
	# check sequence if available for download
	date = get_date(cache_url.replace(date_str,str(seq)))
	if(date != "YYYYMMDD"):
		logger.info("sequence is available for download, updating cache")
		print "sequence is available for download, updating cache"	
		cache.set('DEFAULT', date, str(seq))	# lookup
		cache.set('DEFAULT', str(seq), date)	# reverse lookup
		# write cache to file
		write_cache(cache_file)	
		return str(seq)

	# if not found return empty	
	return ""

def get_prev_seq(seq):

	# check if seq is less than min_seq
	try:		
		if(int(seq) < config.getint('CONFIG','min_seq')):
			return ""
	except Exception, e:
		logger.error("invalid sequence [%s]: (%s)", seq, e)
		print "invalid sequence [" +seq+ "]: " +str(e)
		return ""

	# check sequence if available for download
	s = check_seq(seq)
	if(s != ""):
		return s

	logger.info("getting prev sequence for %s", seq)
	print "getting prev sequence for " +seq
		
	# get prev sequence
	max_days = config.getint('CONFIG','max_days') # max days to search
	for x in range(1, max_days+1):
		seq=int(seq) - x # get prev sequence
		if(cache.has_option('DEFAULT',str(seq))):
			logger.info("sequence found (%s)", str(seq))
			print "sequence found (" +str(seq) +")"
			return str(seq)
			
	# if not found return empty
	return ""
	
def get_next_seq(seq):

	# check if seq is greater than max_seq
	try:		
		if(int(seq) > config.getint('CONFIG','max_seq')):
			return ""
	except Exception, e:
		logger.error("invalid sequence [%s]: (%s)", seq, e)
		print "invalid sequence [" +seq+ "]: " +str(e)
		return ""	

	# check sequence if available for download
	s = check_seq(seq)
	if(s != ""):
		return s

	logger.info("getting next sequence for %s", seq)
	print "getting next sequence for " +seq
		
	# get next sequence
	max_days = config.getint('CONFIG','max_days') # max days to search
	for x in range(1, max_days+1):
		seq=int(seq) + x # get next sequence
		if(cache.has_option('DEFAULT',str(seq))):
			logger.info("sequence found (%s)", str(seq))
			print "sequence found (" +str(seq) +")"
			return str(seq)
			
	# if not found return empty
	return ""	

def list_dates():
	logger.info("listing dates to download")

	global _start_date
	global _start_seq
	global _end_date
	global _end_seq
	global _all
	
	if(_all == "yes"):
		_start_seq = config.get('CONFIG','min_seq')

	# check if valid start sequence
	if not(len(_start_seq) == 0 or cache.has_option('DEFAULT',_start_seq)):
		logger.warn("invalid start sequence (%s)", _start_seq)
		print "invalid start sequence (" +_start_seq+ ")"
		_start_seq = get_prev_seq(_start_seq)
		logger.info("setting start sequence to (%s)", _start_seq)
		print "setting start sequence to (" +_start_seq+ ")"

	# check if valid end sequence
	if not(len(_end_seq) == 0 or cache.has_option('DEFAULT',_end_seq)):
		logger.warn("invalid end sequence (%s)", _end_seq)
		print "invalid end sequence (" +_end_seq+ ")"
		_end_seq = get_next_seq(_end_seq)
		logger.info("setting end sequence to (%s)", _end_seq)
		print "setting end sequence to (" +_end_seq+ ")"

	# check if valid start date
	if not(len(_start_date) == 0 or cache.has_option('DEFAULT',_start_date)):
		logger.warn("invalid start date (%s)", _start_date)
		print "invalid start date (" +_start_date+ ")"
		_start_date = get_prev_date(_start_date)
		logger.info("setting start date to (%s)", _start_date)
		print "setting start date to (" +_start_date+ ")"

	# check if valid end date
	if not(len(_end_date) == 0 or cache.has_option('DEFAULT',_end_date)):
		logger.warn("invalid end date (%s)", _end_date)
		print "invalid end date (" +_end_date+ ")"
		_end_date = get_next_date(_end_date)
		logger.info("setting end date to (%s)", _end_date)
		print "setting end date to (" +_end_date+ ")"
		
	# check if start date is specified
	if(cache.has_option('DEFAULT',_start_date)):
		_start_seq = cache.get('DEFAULT',_start_date)	

	# check if end date is specified
	if(cache.has_option('DEFAULT',_end_date)):
		_end_seq = cache.get('DEFAULT',_end_date)
		
	if(len(_start_seq) == 0 or len(_end_seq) == 0 ):
		find_date()
	
	logger.info("start seq: %s", _start_seq)
	logger.info("start date: %s", _start_date)
	logger.info("end seq: %s", _end_seq)
	logger.info("end date: %s", _end_date)
	print "START: "+_start_date+ " (" +_start_seq+ ")"
	print "END: "+_end_date+ " (" +_end_seq+ ")"

	# check if start sequence is higher than end sequence
	if(_start_seq > _end_seq):
		print "start date is later than end date! exiting..."
		logger.error("start date is later than end date! exiting...")
		sys.exit(1)	

	sleep_time = config.getint('CONFIG','sleep_time')
	for x in range(int(_start_seq), int(_end_seq)+1):
		if(cache.has_option('DEFAULT',str(x))):
			date = cache.get('DEFAULT',str(x))
			logger.debug("%d : %s", x, date)
			print "downloading data : " + date + " (" +str(x)+ ")"
			logger.info("downloading data : %s (%d)", date, x)
			download_date(x, date)
		time.sleep(sleep_time)

def get_date(url):
	logger.debug("loading url: [%s]", url)
	try:
		r = urllib2.urlopen(url)
	except Exception, e:
		logger.error("failed to open url [%s]: (%s)", url, e)
		print "failed to open url [" +url+ "]: " +str(e)	
	
	try:
		filename = r.info()['Content-Disposition'].split('filename=')[-1].replace('"','').replace(';','')
	except KeyError:
		filename = os.path.basename(urllib2.urlparse.urlparse(r.url).path)

	logger.debug("filename: [%s]", filename)

	# if error, return blank date as "YYYYMMDD"
	if(filename == "CustomErrorPage.aspx"):
		return "YYYYMMDD"
		
	# get date (YYYYMMDD) from filename (TC_YYYYMMDD.txt)
	date = filename.split('_')[1].split('.')[0]
	return date


def write_cache(file):
	logger.debug("writing cache file [%s]", file)
	
	# write data to file
	try:
		with open(file, 'wb') as cachefile:
			cache.write(cachefile)
		logger.debug("cache writen to file")
	except Exception, e:
		logger.error("failed to write cache (%s)", e)
		print "failed to write cache" + str(e)	
		
def rebuild_cache(file, start, end):
	logger.info("rebuilding cache file [%s] from %d to %d", file, start, end)

	cache_url = config.get('CONFIG','CACHE_URL')
	date_str = config.get('DEFAULT','DATE_STR')
	sleep_time = config.getint('CONFIG','sleep_time')
	max_days = config.getint('CONFIG','max_days')

	for x in range(start, end+max_days):
		date = get_date(cache_url.replace(date_str,str(x)))
		logger.info("%s = %s", date, str(x))
		if(date != "YYYYMMDD"):
			cache.set('DEFAULT', date, str(x))	# lookup
			cache.set('DEFAULT', str(x), date)	# reverse lookup
		time.sleep(sleep_time)
	
	# write cache to file
	write_cache(file)

def load_cache(file):
	logger.info("loading cache file [%s]", file)
	
	# load cache file
	try:
		fp = open(file)
	except Exception, e:
		logger.debug("exception (%s)", e)
		logger.warn("failed to open cache file [%s]", file)
		logger.info("rebuilding cache [%s]", file)
		logger.info("may take some time to complete, grab a coffee first")
		print "cache file is missing!"
		print "rebuilding cache..."
		print "may take some time to complete, grab a coffee first!"
		# rebuild cache file from min to max
		min = config.getint('CONFIG','min_seq')
		max = config.getint('CONFIG','max_seq')
		rebuild_cache(file, min, max)
	
	# read cache file
	cache.read(file)
	
	logger.debug("displaying cache values!")	
	for (key, val) in cache.items('DEFAULT'):
		logger.debug("  %s = %s", key, val)
			
	logger.info("cache file [%s] has been loaded!", file)

def init_logger(date_fmt, log_level, log_dir, name):
	numeric_level = getattr(logging, log_level.upper(), None)
	if not isinstance(numeric_level, int):
		raise ValueError('Invalid log level: %s' % log_level)

	now = datetime.datetime.now()	
	logger.setLevel(numeric_level)
	rfh = logging.handlers.TimedRotatingFileHandler(filename=log_dir + '/' + name + '_'+ now.strftime('%Y%m%d')+ '.log', when='midnight')
	fmtr = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt=date_fmt)
	rfh.setFormatter(fmtr)
	logger.addHandler(rfh)

	logger.debug("logger has been initialized!")

def update_config(file):
	logger.debug("updating config file [%s]", file)
	# write data to file
	try:
		with open(file, 'wb') as cfgfile:
			config.write(cfgfile)
		logger.debug("cache writen to file")
	except Exception, e:
		logger.error("failed to write cache (%s)", e)
		print "failed to write cache" + str(e)
	
def load_config(file):
	print "loading config file [" +file+ "]"

	# load config file
	try:
		fp = open(file)
	except Exception, e:
		print "failed to open config file [" +file+ "]"
		print str(e)
		sys.exit(1)
		
	config.read(file)

	# check data directory
	data_dir = config.get('CONFIG','DATA_DIR')
	if (not os.path.exists(data_dir)):
		print "creating directory [" +data_dir+ "]"
		os.mkdir(data_dir)

	# check log directory
	log_dir = config.get('CONFIG','LOG_DIR')
	if (not os.path.exists(log_dir)):
		print "creating directory [" +log_dir+ "]"
		os.mkdir(log_dir)

	init_logger(config.get('CONFIG','LOG_DATE_FMT'), config.get('CONFIG','LOG_LEVEL'), config.get('CONFIG','LOG_DIR'), config.get('CONFIG','LOG_FILE_PREFIX'))
	
	logger.debug("displaying config values!")

	for section_name in config.sections():
		logger.debug("[SECTION]: %s", section_name)
		logger.debug("  Options:%s", config.options(section_name))
		for name, value in config.items(section_name):
			logger.debug("  %s = %s", name, value)

	logger.info("config file [%s] has been loaded!", file)
	

def setStartDate(x):
	global _start_date
	print "setting start date: " +x
	_start_date = x

def setEndDate(x):
	global _end_date
	print "setting end date: " +x
	_end_date = x
	
def setStartSeq(x):
	global _start_seq
	print "setting start sequence: " +x
	_start_seq = x
	
def setEndSeq(x):
	global _end_seq
	print "setting end sequence: " +x
	_end_seq = x

def setAll(x):
	global _all
	print "setting to download all available files: " +x
	_all = x
	
def main():
	init_global()
	parser = argparse.ArgumentParser(description='SGX Auto Downloader')
	parser.add_argument('config_file', type=argparse.FileType('r'),
                    help='configuration file')
	parser.add_argument('--setStartSeq', type=setStartSeq,
                    help='set starting sequence [int]')
	parser.add_argument('--setEndSeq', type=setEndSeq,
                    help='set ending sequence [int]')	
	parser.add_argument('--setStartDate', type=setStartDate,
                    help='set starting date [yyyymmdd]')
	parser.add_argument('--setEndDate', type=setEndDate,
                    help='set ending date [yyyymmdd]')
	parser.add_argument('--setAll', type=setAll,
                    help='set to download all available files [yes|no]')					
	args = parser.parse_args()	
	load_config(config_file)
	load_cache(config.get('CONFIG','cache_file'))	
	list_dates()

if __name__ == '__main__':
    main()