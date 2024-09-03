# Configuration settings like API base URL, timeout settings, etc.
# Optionally, may include environment variable management here.

BASE_URL = "https://api.sleeper.app/v1/"

# this tells us the default behavior for the API wrapper. 
# True = convert everything to object oriented version
# False = return raw json results with no object oriented conversion
CONVERT_RESULTS = True
# TO DO: implement way for package user to specify this:
# ex:
# class Config:
#     def __init__(self):
#         # Default configuration
#         self.CONVERT_RESULTS = True

#     def set_convert_results(self, value: bool):
#         self.CONVERT_RESULTS = value

#     def get_convert_results(self) -> bool:
#         return self.CONVERT_RESULTS

# # Create a global config instance
# config = Config()
# then in the files, instead of importing CONVERT_RESULTS I can instead:
# import it: from sleeper_fantasy_api.config import config
# reference it: result = config.get_convert_results()

# user could specify globally by doing something like:
# from sleeper_fantasy_api.config import config
# config.set_convert_results(False)


from datetime import datetime
DEFAULT_SEASON = datetime.now().year


from datetime import datetime, timedelta
CACHE_DURATION = timedelta(days=1)