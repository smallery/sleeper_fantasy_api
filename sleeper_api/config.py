# Configuration settings like API base URL, timeout settings, etc.
# Optionally, may include environment variable management here.

BASE_URL = "https://api.sleeper.app/v1/"

# this tells us the default behavior for the API wrapper. 
# True = convert everything to object oriented version
# False = return raw json results with no object oriented conversion
CONVERT_RESULTS = True

from datetime import datetime
DEFAULT_SEASON = datetime.now().year


from datetime import datetime, timedelta
CACHE_DURATION = timedelta(days=1)