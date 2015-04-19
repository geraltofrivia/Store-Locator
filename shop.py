import os
import cgi
import datetime
import jinja2
import webapp2

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
		_shop = self.request.cookies.get('shop')
		_session = self.request.cookies.get('session_shop')
		#self.response.headers.add_header('Set-cookie','user = %s'%str(""))
		#self.response.headers.add_header('Set-cookie','session = %s'%str(""))
		print "check_cookies: ", _shop, _session
		if logout:
			_shop = datastore.Shops.logout(_shop,_session)
			self.response.headers.add_header('Set-cookie','shop = %s'%str(""))
			self.response.headers.add_header('Set-cookie','session_shop = %s'%str(""))
			return _shop

		shop = datastore.Shops.checkValidSession(_shop,_session)
		print "check_cookies shop found", shop
		return shop

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

class RegistrationPage(Handler):
	def get(self):
		self.response.headers['Content-Type']='text/html'
		self.render("shop_reg.html")

	def post(self):
		register_status = 0
		error = ''
		_fname=self.request.get('fname')
		_lname=self.request.get('lname')
		_email=self.request.get('email')
		_password=self.request.get('pwd')
		_c_password=self.request.get('crpwd')
		_mobile=self.request.get('mobile')
		_shop_name=self.request.get('shop_name')
		_shop_address=self.request.get('shop_add')

		_fname,error_fname = utils.verify_name(_fname)
		_lname,error_lname = utils.verify_name(_lname)
		_email,error_email = utils.verify_email(_email)
		_password,error_password = utils.verify_passwords(_password,_c_password)
		_mobile,error_mobile = utils.verify_mobile(_mobile)
		_shop_name,error_name = utils.verify_text(_shop_name)
		_shop_address,error_address = utils.verify_text(_shop_address)

		print "/registration-post: fname", _fname
		print "/registration-post: lname", _lname
		print "/registration-post: email", _email
		print "/registration-post: mobile", _mobile
		print "/registration-post: shopname", _shop_name
		print "/registration-post: shopaddress", _shop_address
		print "/registration-post: password", _password

		if _fname != '-1' and _lname != '-1' and _email != '-1' and _password != '-1' and _mobile != '-1' and _shop_address != '-1' and _shop_name != '-1':
			register_status,error = datastore.Shops.register(_email,_fname,_lname,_password,_mobile,_shop_name,_shop_address)
			if error == 'Success':
				print "/registration-post: ", register_status
			else:
				self.render("shop_reg.html", error = "This email id is already in use", fname = _fname, lname = _lname, email = _email, mobile = _mobile, shop_name = _shop_name, shop_add = _shop_address)
		else:
			print "/registration-post: incorrect inputs"
			if error_fname == 'Success':
				error_fname = None
			else:
				_fname = None
			if error_lname == 'Success':
				error_lname = None
			else:
				_lname = None
			if error_email == 'Success':
				error_email = None
			else:
				_email = None
			if error_password == 'Success':
				error_password = None
			if error_mobile == 'Success':
				error_mobile = None
			else:
				_mobile = None
			if error_name == 'Success':
				error_name = None
			else:
				shop_name = None
			if error_address == 'Success':
				error_address = None
			else:
				shop_address =  None

			self.render("shop_reg.html", error = error, fname = _fname, lname = _lname, email = _email, mobile = _mobile, shop_name = _shop_name, shop_add = _shop_address, error_fname = error_fname, error_lname = error_lname, error_email = error_email, error_name = error_name, error_mobile = error_mobile, error_password = error_password, error_address = error_address)
			return

		print "/registration-post: successfully registered"
		self.redirect("/shop/#login")

class MainPage(Handler):
	def get(self):
		_shop =  self.check_cookies(self)
		if _shop != -1:
			print "mainpage-get: found shop", _shop
			self.redirect("/shop/profile")
		else:
			print "mainpage-get: no shop found in cookies"
			self.render("shop_home.html")

	def post(self):
		#LOGIN Feature
		_email = self.request.get('email')
		_password = self.request.get('password')

		print "mainpage-post: ", _email, _password
		_password = utils.encrypt(_password)
		_shop = datastore.Shops.login(_email,_password)

		if _shop[0] == -1:
			print "mainpage-post: incorrect credentials"
			self.render("shop_home.html", error = "Invalid username or password", email = _email)
		else:
			print "mainpage-post: shop logged in", _shop
			self.response.headers.add_header('Set-cookie','shop = %s' % _shop[1].key.id())
			self.response.headers.add_header('Set-cookie','session_shop = %s' % _shop[0])
			self.redirect("/shop/profile")

class ProfilePage(Handler):
	def get(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			print "profile-get: found shop", _shop
			products = []
			for product in _shop.inventory:
				p = datastore.Products.fetch_by_id(product.id())
				c = p.category.get()
				products.append((p,c))
				#print products
			a = 'False'
			if _shop.open:
				a = 'True'
			
			if _shop.verified:
				error_verified = None
			else:
				error_verified = "Please verify your profile, by clicking on the link providied in the email to your ID."

			if not _shop.location:
				error_location = "Please input the location of your shop. Without this data, your shop would not show up in search results"
			else:
				error_location = None


			self.render("shop_profile.html", shopname = _shop.shop_name.upper(), fname = _shop.fname, products = products, open=a, error_verified = error_verified, error_location = error_location)

		else:
			print "profile-get: no shop found in cookies"
			self.redirect("/shop/")

	def post(self):		
		_shop = self.check_cookies(self)
		if _shop != -1:
			length = self.request.get('length')
			print "inventorymanagement :post: ", self.request

			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "inventorymanagement :post: length is not a number", length
			print "inventorymanagement: post: length -", length

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user.
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						#Here for sure i have one by one product key. May or may not be geniuine.
						print "inventorymanagement: post: finding product ids: ", key
						products.append(key)
						datastore.Shops.remove_product(key,_shop.key.id())
				print "inventorymanagement: post: products: ", products
			self.redirect("/shop/profile")
		else:
			self.redirect("/shop/")

class Infopage(Handler):
	def get(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			print "profile-get: found shop", _shop
			
			self.render("shop_info.html" ,fname=_shop.fname,lname=_shop.lname ,email=_shop.email,mobile=_shop.mobile,add=_shop.shop_address,_shopname=_shop.shop_name,shopname = _shop.shop_name.upper())
		else:
			self.redirect("/shop/")

	def post(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			_fname=utils.verify_name(self.request.get('fname'))[0]
			_lname=utils.verify_name(self.request.get('lname'))[0]
			_email=utils.verify_email(self.request.get('email'))[0]
			_mobile=utils.verify_mobile(self.request.get('mobile'))[0]
			_shop_name=utils.verify_name(self.request.get('shop_name'))[0]
			_shop_address=utils.verify_name(self.request.get('shop_add'))[0]

			datastore.Shops.update_info(_fname, _lname, _email, _mobile, _shop_name, _shop_address, _shop)
			self.redirect("/shop/profile")

class LocationPage(Handler):
	def get(self):
		_shop =  self.check_cookies(self)
		if _shop != -1:
			#Authenticated
			print "location-page: found shop", _shop.shop_name
			if _shop.location:
				#print "location-page: trying to detect latitude", _shop.location
				lat = _shop.location.lat
				lon = _shop.location.lon
			else:
				print "location-page: trying to detect latitude. None found"
				lon = 72.629174
				lat = 23.190373
			self.render("shop_updatelocation.html",lat = lat, long = lon,fname=_shop.fname, shopname = _shop.shop_name.upper(), lname = _shop.lname,add=_shop.shop_address,mobile = _shop.mobile)
		else:
			self.redirect("/shop/")
	def post(self):

		_lat=self.request.get('lat')
		_log=self.request.get('long')

		#Sanitize these inputs
		_lat,_log = utils.verify_location(_lat,_log)
		if _lat == 'error' or _log == 'error':
			print "locationpage-post: invalid latitude and longitude ", self.request.get('lat'), self.request.get('long')
			return

		_shop =  self.check_cookies(self)
		if _shop != -1:
			#Authenticated
			print "location-page: found shop", _shop.shop_name
			datastore.Shops.updateLocation(_lat,_log,_shop.key.id())
			self.redirect("/shop/profile")
		else:
			self.redirect("/shop/")

class InventoryAdditionPage(Handler):
	def get(self):
		_shop =  self.check_cookies(self)
		if _shop != -1:
			query =	self.request.get('query')
			category = self.request.get('category')
			print "search: get: FOUND CATEGORY", category
			if query and not category:

				#Run a search disregarding any category based limit
				if len(query) > 0:
					products, categories, status = self.search_products(query)
					if products and categories:
						self.render("shop_addinventory.html", categories = categories, products = products, query = query, shopname = _shop.shop_name)
					else:
						self.render("shop_addinventory.html", error = "No match found. Please try again with a different keyword", query = query, shopname = _shop.shop_name)
				else:
					self.render("shop_addinventory.html", categories =  datastore.Categories.getRoots(), shopname = _shop.shop_name)


			if category and not query:
				#Fetch products of this category.
				categories = utils.remove_similarity(datastore.Categories.fetch_by_id(category,True))
				products = datastore.Products.getProductsInCategories(categories)
				self.render("shop_addinventory.html", categories = categories, products = products)

			if query and category:
				if len(query) > 0:
					#For sure, the query exists and user has logged in
					products, categories, status = self.search_products(query)
					if products and categories:
						#WE did find something!
						#print "search: get: query and category: ", products
						categories = datastore.Categories.fetch_by_id(category,True)
						products = datastore.Products.filterProductInCategories(products,categories)
						self.render("shop_addinventory.html", categories = categories, products = products, query = query, shopname = _shop.shop_name)

			if not query and not category:
				self.render("shop_addinventory.html", categories =  datastore.Categories.getRoots(), shopname = _shop.shop_name)
		else:
			self.redirect("/shop/")

	def post(self):
		_shop =  self.check_cookies(self)
		if _shop != -1:
			length = self.request.get('length')
			print "add-shopping: post: ", self.request

			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "add-shopping: post: length is not a number", length
				print "add-shopping: post: length -", length

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user.
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						products.append(key)
						print "add-shopping: post: finding product ids: ", key
						datastore.Shops.add_product(key,_shop.key.id())
						print "add-shopping: post: products: ", products
						self.redirect("/shop/profile")
		else:
			self.redirect("/shop/")

class InventoryManagementPage(Handler):
	def get(self):
		_shop =  self.check_cookies(self)
		if _shop != -1:
			products = []
			for product in _shop.inventory:
				products.append(datastore.Products.fetch_by_id(product.id()))
				print products
			self.render("shop_profile.html", shop = _shop.fname, products = products)
		else:
			print "inventorymanagement: get: No cookies found. Redirecting"
			self.redirect("/shop/")
	def post(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			length = self.request.get('length')
			print "inventorymanagement :post: ", self.request

			#Sanitizing Length
			try:
				length = int(length)
			except:
				print "inventorymanagement :post: length is not a number", length
			print "inventorymanagement: post: length -", length

			if length.__class__ == int('1').__class__ :
				#Surely length is a valid length and we have products list and a valid user.
				#It doesnt
				products = []
				for i in range(length):
					key = self.request.get('%s' % i)
					if key:
						#Here for sure i have one by one product key. May or may not be geniuine.
						print "inventorymanagement: post: finding product ids: ", key
						products.append(key)
						datastore.Shops.remove_product(key,_shop.key.id())
				print "inventorymanagement: post: products: ", products
			self.redirect("/shop/inventory")
		else:
			self.redirect("/shop/")

class PasswordChange(Handler):
	def get(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			print "updatepassword: rendering password page"
			self.render("shop_password.html",shopname=_shop.shop_name.upper(),fname=_shop.fname,lname=_shop.lname)
		else:
			print "updatepassword: redirecting to home page"
			self.redirect("/shop")

	def post(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			_old_pass = self.request.get('crpwd')
			_new_pass = self.request.get('nwpwd')
			_cnew_pass = self.request.get('cnwpwd')

			_new_pass = utils.verify_passwords(_new_pass,_cnew_pass)[0]
			if not _new_pass == '-1':
				if datastore.Shops.update_password(_old_pass,_new_pass,_shop):
					self.redirect("/shop/profile?msg=Password_successfully_changed",shopname=_shop.shop_name.upper(),fname=_shop.fname,lname=_shop.lname)
				else:
					self.render("shop_password.html", error = "Wrong password entered",shopname=_shop.shop_name.upper(),fname=_shop.fname,lname=_shop.lname)
			else:
				self.render("shop_password.html", error = "Passwords do not match",shopname=_shop.shop_name.upper(),fname=_shop.fname,lname=_shop.lname)
		else:
			self.redirect("/shop/")

class LogoutPage(Handler):
	def get(self):
		url =  self.request.get('url')
		print "INITIATING LOGOUT ", url
		self.check_cookies(self,logout = True)
		self.redirect(url)

class ShopProfile(Handler):
	def get(self, url):
		print url
		_shop=datastore.Shops.fetch_by_id(str(url))
		if _shop:
			if _shop.verified:
				products = []
				for product in _shop.inventory:
					p = product.get()
					c = p.category.get()
					products.append((p,c))
				self.render("shop_view_cust.html",fname=_shop.fname,lname=_shop.lname,email=_shop.email,add=_shop.shop_address,shopname=_shop.shop_name,mobile=_shop.mobile,products = products, lat = _shop.location.lat, lon = _shop.location.lon)
			else:
				self.redirect('/shop/')
		else:
			self.redirect('/shop/#login')
			
class ShopOpenClose(Handler):
	def get(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			value = self.request.get('switch')
			print "shopopenclose: get: ", value
			if str(value) == 'open':
				datastore.Shops.open_shop(_shop)
			elif str(value) == 'close':
				datastore.Shops.close_shop(_shop)
		self.redirect('/shop/#login')

class VerifyShop(Handler):
	def get(self):
		randstring = self.request.get('code')
		print randstring
		if randstring:
			datastore.Verification.verify_shop(str(randstring))
		self.redirect("/shop/#login")

class Temp(Handler):
	def get(self):
		_shop = self.check_cookies(self)
		if _shop != -1:
			utils.email_verification(_shop,'11L24HG7UHMJ5LVD0J6D')

application = webapp2.WSGIApplication([('/shop/registration',RegistrationPage),
									 ('/shop/register',RegistrationPage),
									 ('/shop/profile',ProfilePage),
									 ('/shop/location',LocationPage),
									 ('/shop/addinventory',InventoryAdditionPage),
									 ('/shop/inventory',InventoryManagementPage),
									 ('/shop/logout',LogoutPage),
									 ('/shop/editinfo',Infopage),
									 ('/shop/updatepassword',PasswordChange),
									 ('/shop/shopprofile/(\d+)',ShopProfile),
									 ('/shop/openclose',ShopOpenClose),
									 ('/shop/',MainPage),
									 ('/shop/verify',VerifyShop),
									 ('/shop/temp',Temp)
									 ], debug=True)
