"""
Functions: 
setCity(city)
getCity(city)
getMoviesNowShowing()
getMovieImageURL(movie_name)
getMovieBookingURL(city, movie_name)
getMultipleDimensions(city, movie_name)
getMultiplexes(city, movie_name)
getVenueShowDetails(city, movie_name)
"""


from bs4 import BeautifulSoup
from requests import get
from json import dump, load, loads
from time import time
from os import remove
from pprint import pprint


class BookMyShow():
	baseUrl = "https://in.bookmyshow.com"		
	def __init__(self, city, event="movies"):
		self.__city = city.lower()
		self.__urls = dict()
		# self.__urls = {
		# 	"city": self.baseUrl + "{city}/{event}".format(city=self.__city, event=event),
		# 	"validity": -1 if 'validity' not in self.__urls else self.__urls['validity']
		# }


	def setCity(self, city):
		self.__init__(city)
	
	def getCity(self):
		return self.__city
	
	def getUrls(self):
		"""
		Returns a dictionary of urls
		__urls: {
			"pune": {
				"name": "pune",
				"all_movies_url": "https://in.bookmyshow.com/pune/movies",
				"movie_urls": {
					"<Movie Name>": {
						"name": "<Movie Name>",
						"booking_url": "<Booking URL with movie code>",
						"image_url": "<Image URL>" 
					}
				},
				"validity": <Time in millis>
			}
		}
		"""
		try: 
			self.__urls = self.loadFromFile('__urls.json')
			# print(self.__urls[self.__city]['all_movies_url'], self.__urls[self.__city]['validity'])
			if self.__city not in self.__urls:
				raise Exception("Data for {} not found.".format(self.__city))
			if not self.isValid(self.__urls[self.__city]):
				raise Exception("Old data invalidated")
		except Exception as e:
			print(e)
			print("Downloading new Data.")
			self.__urls[self.__city] = {
				"name": self.__city,
				"all_movies_url": self.baseUrl + "/{city}/{event}".format(city=self.__city, event="movies")
			}
			bmsNowShowingContent = get(self.__urls[self.__city]['all_movies_url'])
			if bmsNowShowingContent.status_code == 404:
				raise ValueError('City not supported')
				# city name must be some synonym
				# See log file to correct this error
			else:
				soup = BeautifulSoup(bmsNowShowingContent.text, 'html5lib') 
				self.__urls[self.__city]['movie_urls'] = dict()
				# Valid till next day
				print(soup.title.string)
				for tag in soup.find_all("div", {"class": "movie-card-container"}):
					img = tag.find("img", {"class": "__poster __animated"})
					movie = {}
					movie['name'] = img['alt']
					movie['booking_url'] = tag.find('a', recursive=True)['href']
					movie['image_url'] = img['data-src']
					# print(movie)
					self.__urls[self.__city]['movie_urls'][movie['name']] = movie
				self.__urls[self.__city]['validity'] = int(round(time()*1000)) + (1000 * 60 * 60 * 24)
				if len(self.__urls[self.__city]['movie_urls']) <= 0:
					raise Exception("Data not received from BookMyShow.com")
				self.writeToFile('__urls.json', self.__urls)
				return self.__urls
		else:
			return self.__urls
		
	def writeToFile(self, fileName, data):
		try:
			with open(fileName, "w") as outfile:
				dump(data, outfile, indent=4)
		except Exception as e:
			print("Error occurred while saving to {filename}: {error}".format(fileName=fileName, error=e))
			remove(fileName)
		
	def loadFromFile(self, fileName):
		with open(fileName) as infile:
			return load(infile)

	def isValid(self, a):
		# print(a['validity'], int(round(time()*1000)))
		if a['validity'] < int(round(time()*1000)):
			return False
		return True


	def getMoviesNowShowing(self):
		moviesNowShowing = []
		try: 
			self.getUrls()
		except ValueError as e: # City not Supported
			return e
		else: 
			# print(self.__urls)
			for movie in self.__urls[self.__city]['movie_urls'].keys():
				moviesNowShowing.append(movie)
			return moviesNowShowing

	def getAvailableLanguageDimensions(self, movie_name):
		"""
		langAndDimes: {
			"<Language>": {
				"language": "<Language>",
				"<Dimension>": {
					"dimension": "<Dimension>",
					"url": <booking_in_language_and_dimension>
				}
			} 
		}
		"""
		try: 
			self.getUrls()
		except ValueError as e: # City not Supported
			return e
		else:
			if movie_name not in self.__urls[self.__city]['movie_urls']:
				raise Exception("Movie not found in {city}".format(city=self.__city))
			booking_url = self.baseUrl + self.__urls[self.__city]['movie_urls'][movie_name]['booking_url']
			print(booking_url)
			movie_page_content = get(booking_url)
			if movie_page_content.status_code != 200:
				raise Exception("Network error, please try again")
			
			soup = BeautifulSoup(movie_page_content.text, 'html5lib')

			langAndDimen = {}
			tag = soup.find("div", {"id": "languageAndDimension"})
			for langs in tag.find_all("div", {"class": "format-heading"}):
				language = langs.text.strip()
				langAndDimen[language] = {
					"language": language
				}
				dimensions = langs.next_sibling.next_sibling
				for dimen in dimensions.find_all("a", {"class": "dimension-pill"}):
					langAndDimen[language][dimen.text] = {
						"dimension": dimen.text,
						"url": dimen['href']
					}
			return langAndDimen

		
	def getVenueShowDetails(self, url):
		"""
		"details": [{
			"name": "Abhiruchi City Pride: Sinhagad Road",
			"timings": [
				"show_time": "06:30 PM",
				"seat_type": [
					{
						"name": "ROYAL SOFA",
						"price": "360.00",
						"availability": "Sold Out"
					}
				]
			]
		}]
		"""

		theatres_page_content = get(url)
		soup = BeautifulSoup(theatres_page_content.text, 'html5lib')
		print(soup.title.string)

		venue_data = []
		venues = soup.find("ul", {"id": "venuelist"})
		for venue in venues.find_all("li", {"class": "list"}):
			venue_name = venue.find("a", {"class": "__venue-name"}).text.strip()
			# print(venue_name)
			current_venue = {}
			current_venue['name'] = venue_name
			current_venue['timings'] = []
			for timings in venue.find_all("a", {"class": "__showtime-link"}):
				# print(timings.text.strip(), timings['data-cat-popup'])
				current_timing = {}
				current_timing['show_time'] = timings.text.strip()[:8]
				current_timing['seat_type'] = []

				data_cat = loads(timings['data-cat-popup'])
				for seat in data_cat:
					current_seat = {}
					current_seat["name"] = seat['desc']
					current_seat['price'] = seat['price']
					current_seat['availability'] = seat['availabilityText']
					current_timing['seat_type'].append(current_seat)
				current_venue['timings'].append(current_timing)
			venue_data.append(current_venue)	
		self.writeToFile("details.json", {"details": venue_data})
		return {
			"details": venue_data
		}

		
	
def test():
	city = "Pune"
	bms = BookMyShow(city)
	while True:
		# city = input("Enter city: ")	
		bms.setCity(city)
		# print("City:", bms.getCity())
		print(bms.getMoviesNowShowing())
		# movie_name = input("Movie name: ")
		movie_name = "Avengers: Endgame"
		langAndDimes = bms.getAvailableLanguageDimensions(movie_name)
		pprint(langAndDimes, indent=4)
		url = bms.baseUrl + langAndDimes['English']['2D']['url']
		pprint(bms.getVenueShowDetails(url))
		again = input("Again: ")
		if again == "n":
			break
	# print(bms.getUrls())
	

if __name__ == "__main__":
	test()

	

	
		