import os
import cgi
import datetime
import jinja2
import webapp2
import math

import datastore		#Our databases
import utils			#Misc utility class

print "Server starting"
#Setup templating engine - Jinja2
template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),autoescape = True)
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.write(*a,**kw)

	def render_Str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_Str(template, **kw))

	def check_cookies(self, handler, logout = False):
		_user = handler.request.cookies.get('user')
		_session = handler.request.cookies.get('session')
		if logout:
			_user = datastore.Users.logout(_user,_session)
			self.response.headers.add_header('Set-cookie','user = %s'%str(""))
			self.response.headers.add_header('Set-cookie','session = %s'%str(""))
			return _user

		_user = datastore.Users.checkValidSession(_user,_session)
		print "CHECKCOOKIES User found", _user
		return _user

	def search_products(self, query):

		#print query
		categories = []
		products = []
		products_category = []
		products_brand = []
		brands = []
		found_category = False		
		found_brand = False
		found_products = False
		done =  False

		#First try to locate category.
		#Here i am assuming that if we have found a match for category, then we don't need to investigate on this front further. Simply return a one tuple list in the function
		#Further, simply fetch products relevent to the category and proceed to render them.
		categories = datastore.Categories.locate(query)
		#print categories
		if utils.found_match(categories):
			found_category = True
			print "search: get : found category", categories
			categories = utils.return_match(categories)
			products_category +=  utils.add_similarity(datastore.Products.getProductsInCategory(categories[0][0]))		#Added dummy similarity only for the sake of further operations
			categories += datastore.Categories.getChildren(categories[0][0])
			#Categories now have children & we also have products to show.

		# Then we attempt a brand match
		brands = datastore.Products.searchBrand(query)
		if utils.found_match(brands):
			found_brand = True
			print "search: get : found brand!"
			brands = utils.return_match(brands)
			products_brand += utils.add_similarity(datastore.Products.getProductsInBrands(brands[0][0]))				#Added dummy similarity only for the sake of further operations
			#Now we have products of a brand to show!

		#print "Reached Here"
		#Then we proceed to find some relevent products
		products = utils.sort(datastore.Products.searchProduct(query,_ease = 70))		
		if utils.found_match(products):
			#We have found some products spot on. So now simply render these products 
			#along with some products from the brand and some from the categories. (If they were spot on too!)
			products = utils.return_upto(products,_ease = 85)
			found_products = True

		products = utils.join(products,products_brand,products_category,_distinct = True)
		print "search: get: product lenght: ", len(products)

		#Evaluate our current situation. 
		if not found_brand and not found_products and not found_products:
			#At this point, assuming we have neither products or brands or categories match or even products match!
			#We search for categories in a relaxed manner. And we search for products. Forget brand!
			categories = datastore.Categories.search(query,_ease = 70,_getchild = True)
			brands =  datastore.Products.searchBrand(query,_ease = 70)

			if len(categories) > 0:
				products_category +=  utils.add_similarity(datastore.Products.getProductsInCategories(utils.remove_similarity(categories)))
				if utils.found_match(categories,_ease = 80):
					found_category = True
			if len(brands) > 0:
				if utils.found_match(brands,_ease = 80):
					found_brand = True
				products_brand += utils.add_similarity(datastore.Products.getProductsInBrands(utils.remove_similarity(brands)))

			#We might not have any meaningful search but we have found some products.
			products = utils.join(products,products_brand,products_category,_distinct = True)
			if len(products) > 1:
				#Just simply render these products and categories and be done with it.
				done = True

		else:
			done = True

		####################### We are done finding products. Now second and easier part!####################

		if done:
			#We have two arrays to show.
				#Products
				#Categories

			#Change! categories will always reflect the products selected!
			categories = utils.add_similarity(datastore.Products.getCategoriesForProducts(utils.remove_similarity(products)))

			#Finally render the two arrays	
			return utils.remove_similarity(products), utils.remove_similarity(categories), "Found"

		else:
			#If we are still not done, it could mean only one thing that we have not found any match whatsoever!
			#Throw error message
			return None, None, "Nothing Found"

class Registration(Handler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/html'
		self.render("customer_registration.html")

	def post(self):
		register_status = 0 #If status = 0, so far success. If it goes -1, something's wrong
		error = ''
		self.response.headers['Content-Type'] = 'text/html'
		_fname = self.request.get('fname')
		_lname = self.request.get('lname')
		_email=self.request.get('email')
		_password = self.request.get('pwd')
		_c_password = self.request.get('crpwd')


		_fname,error_fname = utils.verify_name(_fname)
		_lname,error_lname = utils.verify_name(_lname)
		_email,error_email = utils.verify_email(_email)
		_password,error_password = utils.verify_passwords(_password,_c_password)
		
		if _fname != '-1' and _lname != '-1' and _email != '-1' and _password != '-1':
			register_status,error = datastore.Users.register(_fname,_lname,_email,_password)	#Now contains user key
			if error == 'Success':
				print "/registration-post: ", register_status
			else:
				self.render("customer_registration.html", error = "This email ID already exists", fname = _fname, lname = _lname, email = _email)
		else:
			if error_fname == 'Success':
				error_fname = None
			else:
				_fname = ""
			if error_lname == 'Success':
				error_lname = None
			else:
				_lname = ""
			if error_email == 'Success':
				error_email = None
			else:
				_email = ""
			if error_password == 'Success':
				error_password = None

			print "/registration-post : INCORRECT DETECTED"
			self.render("customer_registration.html", error = "Incorrect Details. Please input valid details", fname = _fname, lname = _lname, email = _email, error_fname = error_fname, error_lname = error_lname, error_password = error_password, error_email = error_email)
			return

		print "/registration-post: Successfully Registered"
		#self.response.headers.add_header('Set-cookie', 'user = %s' % register_status[0])
		self.redirect("/")		#Change to homepage.
		#self.render("customer_home.html")
class ProductsPage(Handler):
	def get(self):
		#Categories.populate()
		#Products.populate()
		categories = Products.getAll()
		self.write("<ul>")
		for cat in categories:
			entry = "<li>"+ cat + "</li>"
			self.write(entry)
		self.render("testpage.html")

	def post(self):
		_query = self.request.get('query')
		_category = self.request.get('category')
		#categories = Products.searchProduct(_query)
		#for cat in categories:
		#	entry = "<li>" + cat[0].name + " URL: " + cat[0].key.urlsafe() + " BRAND: " + cat[0].brand + "</li>"
		#	self.write(entry)
		brands = datastore.Products.searchProductsInCategory(_query,_category)
		for b in brands:
			entry = "<li>" + b[0].name + " URL: " + b[0].key.urlsafe() + " BRAND: " + b[0].brand + "</li>"
			self.write(entry)

class PopulatingServer(Handler):
	def get(self):
		datastore.Categories.populate()
		self.write('<form method = "post"> <input type="submit"> </form>')
		
	def post(self):
		datastore.Products.populate()

class MainPage(Handler):
	def get(self):
		#Check for cookies. If exist. or if not!
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			#self.render("customer_profile.html", fname = _user.fname)
			self.redirect('/profile')
		else:
			#self.response.headers.add_header('Set-cookie','user =  guest')
			print "NO COOKIE FOUND ON HOME PAGE"
			self.render("customer_home.html")

	def post(self): 	
		_email = self.request.get('email')
		_password = self.request.get('password')

		_password = utils.encrypt(_password)
		_user = datastore.Users.login(_email,_password)

		if _user[0] == -1:
		 	print "Incorrect credentials"
		 	self.render("customer_home.html", error = "Please recheck your credentials and try again,", email = _email)
		else:
		 	print "User successfully logged in!", _user
		 	self.response.headers.add_header('Set-cookie','user = %s' % _user[1].key.id())
		 	self.response.headers.add_header('Set-cookie','session = %s' % _user[0])
		 	self.redirect("/search")

class LogoutPage(Handler):
	def get(self):
		url =  self.request.get('url')
		print "INITIATING LOGOUT ", url
		self.check_cookies(self,logout = True)
		self.redirect(url)

class SearchPageProduct(Handler):
	def get(self):
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			query =	self.request.get('query')
			category = self.request.get('category')
			print "search: get: FOUND CATEGORY", category
			if query and not category:

				#Run a search disregarding any category based limit
				if len(query) > 0:

					#For sure, the query exists and user has logged in
					products, categories, status = self.search_products(query)
					if products and categories:
						#WE did find something!
						self.render("customer_search.html", categories = categories, products = products, query = query, fname = _user.fname)
					else:
						#No result found
						self.render("customer_search.html", error = "No match found. Please try again with a different keyword", query = query, fname = _user.fname)
				else:
					self.render("customer_search.html", categories =  datastore.Categories.getRoots(), fname = _user.fname)
		

			if category and not query:
				#Fetch products of this category. 
				categories = utils.remove_similarity(datastore.Categories.fetch_by_id(category,True))
				products = datastore.Products.getProductsInCategories(categories)		
						
				self.render("customer_search.html", categories = categories, products = products , fname = _user.fname)

			if query and category:
				if len(query) > 0:
					#For sure, the query exists and user has logged in
					products, categories, status = self.search_products(query)
					if products and categories:
						#WE did find something!
						#print "search: get: query and category: ", products
						categories = datastore.Categories.fetch_by_id(category,True)
						products = datastore.Products.filterProductInCategories(products,categories)
						self.render("customer_search.html", categories = categories, products = products, query = query, fname = _user.fname)
				else:
					self.render("customer_search.html", categories =  datastore.Categories.getRoots(), fname = _user.fname,error="please enter your product")
			if not query and not category:
				self.render("customer_search.html", categories =  datastore.Categories.getRoots(), fname = _user.fname)

		else:
			#self.response.headers.add_header('Set-cookie','user =  guest')
			self.redirect("/")
	
	def post(self):
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			length = self.request.get('length')
			only_open = self.request.get('open_now')
			if only_open:
				only_open = True
			print "search :post: ", self.request			

			if _user.location == None:
				self.redirect('/updatelocation')
				return

			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "search :post: length is not a number", length
			print "search-post: length -", length

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user. 
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						products.append(str(key))
						#print "search-post: finding product ids: ", key
				print "search-post: products: ", products

				
				if len(products) > 0:
					#I have products that the user wants to buy - products
					#I need the shops now.
					barrier = 7.0
					radius = 10.0										#in kms

					match_weight = 3
					distance_weight= 1
					selected_shops = []

					shops = datastore.Shops.query(datastore.Shops.verified == True).fetch()
					#First find matches. then show shops.
					#if lets say i find one shop with 60% match. I might wanna increase the radius to lets say twice to find 80% match. So exponentially weighted then.
					for shop in shops:
						if not shop.location:
							continue
						distance = radius - abs(utils.distance_on_unit_sphere(_user.location.lat, _user.location.lon, shop.location.lat, shop.location.lon))
						match = datastore.Shops.match_products(products,shop)
						index = math.pow(10,distance/radius) + math.pow(10,match/200.0)
						if match > 30:
							index = 0
						print "search: post: index: ", shop.email, shop.location, _user.location, distance, match, index
						#Sort the array based on this index.
						if only_open:
							if shop.open:
								selected_shops.append((shop,index))
						else:		
							selected_shops.append((shop,index))

					selected_shops = utils.sort(selected_shops)
					print "search: post: selectedshops: ", selected_shops
					if len(selected_shops) > 10:
						selected_shops[:10]
							

					#I now have selected shops with me. Now we need to simply run them through an index and show them on the map. That i do not know how to! So lets just print the shops.
					#let is a get a list of cordinate tuples
					cordinates = []
					final_shops = []
					for shop in selected_shops:
						print shop[0].shop_name, shop[1]
						cordinates.append((shop[0].location.lat,shop[0].location.lon))
						final_shops.append((shop[0],round(shop[1],2)))
					self.render("map.html",cordinates = cordinates,shops=final_shops,fname = _user.fname,lname=_user.lname,lat=_user.location.lat,lon= _user.location.lon)
				else:
					self.render("customer_search.html",error="No product selected")
class MaterializeShoppingList(Handler):
	def get(self):
		_user = self.check_cookies(self)
		if _user != -1:
			lat_test = 'a'
			try:
				lat_test = _user.location.lat
			except:
				self.redirect('/updatelocation')
				return

			if not lat_test.__class__ == float(12).__class__:
				self.redirect('/updatelocation')
				return
			
			print "DEBUG", lat_test
			only_open = False
			products = _user.shopping_list

			if len(products) > 0:
				#I have products that the user wants to buy - products
				#I need the shops now.
				barrier = 7.0
				radius = 10.0										#in kms

				match_weight = 3
				distance_weight= 1
				selected_shops = []

				shops = datastore.Shops.query(datastore.Shops.verified == True).fetch()
				#First find matches. then show shops.
				#if lets say i find one shop with 60% match. I might wanna increase the radius to lets say twice to find 80% match. So exponentially weighted then.
				for shop in shops:
					if not shop.location:
						continue
					distance = radius - abs(utils.distance_on_unit_sphere(_user.location.lat, _user.location.lon, shop.location.lat, shop.location.lon))
					match = datastore.Shops.match_products(products,shop)
					index = math.pow(10,distance/radius) + math.pow(10,match/200.0)
					print "search: post: index: ", shop.email, shop.location, _user.location, distance, match, index
					#Sort the array based on this index.
					if only_open:
						if shop.open:
							selected_shops.append((shop,index))
					else:		
						selected_shops.append((shop,index))

				selected_shops = utils.sort(selected_shops)
				print "search: post: selectedshops: ", selected_shops
				if len(selected_shops) > 10:
					for shop in selected_shops:
						if shop[1] < barrier:
							selected_shops.remove(shop)

				#I now have selected shops with me. Now we need to simply run them through an index and show them on the map. That i do not know how to! So lets just print the shops.
				#let is a get a list of cordinate tuples
				cordinates = []
				final_shops = []
				for shop in selected_shops:
					print shop[0].shop_name, shop[1]
					cordinates.append((shop[0].location.lat,shop[0].location.lon))
					final_shops.append((shop[0],round(shop[1],2)))
				self.render("map.html",cordinates = cordinates,shops=final_shops,fname = _user.fname,lname=_user.lname,lat=_user.location.lat,lon= _user.location.lon)
			
			else:
				self.redirect("/profile")

		else:
			self.redirect("/")

class ShoppingListAdd(Handler):
	def get(self):
		#Search for product here!
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			query =	self.request.get('query')
			category = self.request.get('category')
			print "search: get: FOUND CATEGORY", category
			if query and not category:

				#Run a search disregarding any category based limit
				if len(query) > 0:

					#For sure, the query exists and user has logged in
					products, categories, status = self.search_products(query)
					if products and categories:
						#WE did find something!
						self.render("addshoppinglist.html", categories = categories, products = products, query = query,fname=_user.fname)
					else:
						#No result found
						self.render("addshoppinglist.html", error = "No match found. Please try again with a different keyword", query = query,fname=_user.fname)
				else:
					self.render("addshoppinglist.html", categories =  datastore.Categories.getRoots(),fname=_user.fname)
		

			if category and not query:
				#Fetch products of this category. 
				categories = utils.remove_similarity(datastore.Categories.fetch_by_id(category,True))
				products = datastore.Products.getProductsInCategories(categories)					
				self.render("addshoppinglist.html", categories = categories, products = products,fname=_user.fname)

			if query and category:
				if len(query) > 0:
					#For sure, the query exists and user has logged in
					products, categories, status = self.search_products(query)
					if products and categories:
						#WE did find something!
						#print "search: get: query and category: ", products
						categories = datastore.Categories.fetch_by_id(category,True)
						products = datastore.Products.filterProductInCategories(products,categories)
						self.render("addshoppinglist.html", categories = categories, products = products, query = query,fname=_user.fname)

			if not query and not category:
				self.render("addshoppinglist.html", categories =  datastore.Categories.getRoots(),fname=_user.fname)

		else:
			#self.response.headers.add_header('Set-cookie','user =  guest')
			self.redirect("/")
	
	def post(self):
		#Do the real work here!
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			length = self.request.get('length')
			print "add-shopping: post: ", self.request			
			
			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "add-shopping: post: length is not a number", length
			print "sadd-shopping: post: length -", length
			

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user. 
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						products.append(key)
						print "add-shopping: post: finding product ids: ", key
						datastore.Users.add_product(key,_user.key.id())
				print "add-shopping: post: products: ", products
				self.redirect("/profile")
		else:
			self.redirect("/")

class ShoppingListManage(Handler):
	def get(self):
		#Authenticate the user based on cookies. See get of mainpage on how to do so.
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			products = []
			for product in _user.shopping_list:
				products.append(datastore.Products.fetch_by_id(product.id()))
				print products
			self.render("shopping-list.html", user = _user.fname, products = products)
		else:
			#self.response.headers.add_header('Set-cookie','user =  guest')
			print "shoppinglist_manage: get: No cookies found. Redirecting"
			self.redirect("/")

	def post(self):
		#Expect a list of products to delete
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			length = self.request.get('length')
			print "shopping_list :post: ", self.request			
			
			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "shopping_list :post: length is not a number", length
			print "shopping_list-post: length -", length

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user. 
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						#Here for sure i have one by one product key. May or may not be geniuine.
						print "shopping_list-post: finding product ids: ", key
						products.append(key)
						datastore.Users.remove_product(key,_user.key.id())
				print "shopping_list-post: products: ", products
			self.redirect("/shoppinglist")

class LocationPage(Handler):
	def get(self):
		_user =  self.check_cookies(self)
		if _user != -1:
			if _user.location:
				#print "location-page: trying to detect latitude", _shop.location
				lat = _user.location.lat
				lon = _user.location.lon
			else:
				print "location-page: trying to detect latitude. None found"
				lon = 72.629174
				lat = 23.190373
			self.render("customer_map.html",lat = lat, long = lon,fname = _user.fname)
		else:
			self.redirect("/")

	def post(self):

		_lat=self.request.get('lat')
		_log=self.request.get('long')
		
		#Sanitize these inputs
		_lat,_log = utils.verify_location(_lat,_log)
		if _lat == 'error' or _log == 'error':
			print "locationpage-post: invalid latitude and longitude ", self.request.get('lat'), self.request.get('long')
			return 

		_user =  self.check_cookies(self)
		if _user != -1:
			#Authenticated
			print "location-page: found shop", _user.fname
			datastore.Users.updateLocation(_lat,_log,_user)
			self.redirect("/profile")

class ProfilePage(Handler):
	def get(self):
		_user = self.check_cookies(self)
		if _user != -1:
			products = []
			for product in _user.shopping_list:
				p = datastore.Products.fetch_by_id(product.id())
				c = p.category.get()
				products.append((p,c))
				#print products
			if not _user.location:
				error_location = "Please update your location "	
			else:
			    error_location = ""	
			self.render("customer_profile.html" ,fname=_user.fname,lname=_user.lname,email=_user.email,products=products,error=error_location)
		else:
			self.redirect("/")

	def post(self):
		_user = self.check_cookies(self)
		if _user != -1:
			#User exists and cookie is correct.
			length = self.request.get('length')
			print "profile: post: ", self.request			
			
			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "shopping_list :post: length is not a number", length
			print "shopping_list-post: length -", length
			if length==0:
			
				self.redirect("/profile")
				return

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user. 
				#It doesnt
				count=0
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						#Here for sure i have one by one product key. May or may not be geniuine.
						count=count+1
						print "shopping_list-post: finding product ids: ", key
						datastore.Users.remove_product(key,_user.key.id())
				self.redirect("/profile")
				return	
			

class PasswordChange(Handler):
	def get(self):
		_user = self.check_cookies(self)
		if _user != -1:
			self.render("customer_update_pass.html",fname = _user.fname)
		else:
			self.redirect("/")

	def post(self):
		_user = self.check_cookies(self)
		if _user != -1:
			_old_pass = self.request.get('crpwd')
			_new_pass = self.request.get('nwpwd')
			_cnew_pass = self.request.get('cnwpwd')

			_new_pass = utils.verify_passwords(_new_pass,_cnew_pass)[0]
			if not _new_pass == '-1':
				if datastore.Users.update_password(_old_pass,_new_pass,_user):
					self.redirect("/profile?msg=Password_successfully_changed")
				else:
					self.render("customer_update_pass.html", error = "Incorrect Password", fname = _user.fname)
			else:
				self.render("customer_update_pass.html",error = "New passwords do not match, or are of inadequate length.",fname = _user.fname)

		else:
			self.redirect("/")

class ShopRedirection(Handler):
	def get(self):
		self.redirect('/shop/')

class InfoPage(Handler):
	def get(self):
		_user = self.check_cookies(self)
		if _user != -1:
			self.render("customer_info.html" ,fname=_user.fname,lname=_user.lname,email=_user.email)

	def post(self):
		_user = self.check_cookies(self)
		if _user != -1:
			_fname=utils.verify_name(self.request.get('fname'))[0]
			_lname=utils.verify_name(self.request.get('lname'))[0]
			_email=utils.verify_email(self.request.get('email'))[0]
			datastore.Users.update_info(_fname,_lname,_email,_user)
			self.render("customer_info.html" ,fname=_user.fname,lname=_user.lname,email=_user.email)

		else:
			self.redirect("/")

application = webapp2.WSGIApplication([
									('/',MainPage),
									('/products',ProductsPage),
									('/registration',Registration),
									('/admin',PopulatingServer),
									('/logout',LogoutPage),
									('/search',SearchPageProduct),
									('/addshoppinglist',ShoppingListAdd),
									('/shoppinglist',ShoppingListManage),
									('/getshoppinglist',MaterializeShoppingList),
									('/updatelocation',LocationPage),
									('/profile',ProfilePage),
									('/updatepwd',PasswordChange),
									('/shop',ShopRedirection),
									('/editinfo',InfoPage)
									], debug=True)


