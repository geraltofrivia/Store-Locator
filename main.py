import os
import cgi
import datetime
import jinja2
import webapp2
from google.appengine.ext import ndb 

#Custom imports
import catalogue		#TO populate the Categories DB
from fuzzywuzzy import fuzz



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

#Categories DB
class Categories(ndb.Model):
	name = ndb.StringProperty(required = True)
	children = ndb.StringProperty(repeated = True)

	@classmethod
	def populate(self):
		products = catalogue.getCategories()
		for product in products:
			_name = product[0]			#The product name is supposed to be unique. ASSUMED!
			if len(product) > 1:
				_children = product[1]
				entity = Categories(name = _name, children = _children)
			else:
				entity = Categories(name = _name)
			entity.put()

	@classmethod
	def isLeaf(self,_category_key):
		category = _category_key.get()
		if len(category.children) > 0:
			return False
		return True

	@classmethod
	def getLeafs(self,_category_key):
		#To find all the leaf categories. (Which have no children)
		#Will return itself if it is the leaf.
		if self.isLeaf(_category_key):
			return _category_key.get()
		
		category = _category_key.get()
		children = self.getChildren(category)

		while True:
			all_leaves = True
			new_list = []
			for child in children:
				if not self.isLeaf(child.key):
					all_leaves = False
					new_list += self.getChildren(child)
				else:
					new_list.append(child)
			children = new_list
			if all_leaves:
				break

		return children

	@classmethod
	def search(self,_name,_getchild = True,_ease = 90):
		#Get a list of categories which have the argument string in it.
		#query = self.locate(_name,_getchild = True)

		results = []
		query = Categories.query().fetch()
		for q in query:
			similarity = fuzz.partial_ratio(_name.lower(), q.name.lower())
			if similarity >= _ease:
				results.append(q)
			if similarity == 100:
				results = [q]
				break

		if _getchild:
			for q in results:
				children += self.getChildren(q)

		return results

	@classmethod
	def getAll(self):
		query = self.query()
		categories = []
		for category in query: categories.append(category.name + " " +category.key.urlsafe())
		#print categories
		return categories

	@classmethod
	def getProducts(self,key = ''):
		query = Products.query(Products.category == key)
		return query.fetch()

	@classmethod 	#Obsolete method of dumb  but fast keyword finding. Use only for quick results
	def locate_primitive(self,_name,getchild = False):
		#simply does a strict string match search. MAY RETURN MORE THAN ONE RESULT!
		query = Categories.query(Categories.name == _name).fetch()
		children = []
		if getchild:
			for q in query:
				child = self.getChildren(q)
				for c in child:
					children.append(c)
		query += children
		return query

	@classmethod
	def locate(self,_name,_getchild = False, _ease = 85):
		results = []
		children = []
		query = ndb.gql("SELECT * FROM Categories")
		for q  in query:
			similarity = fuzz.ratio(_name.lower(),q.name.lower())
			if similarity == 100:
				results = [q]
				break
			if similarity >= _ease:
				results.append(q)

		if _getchild:
			for q in results:
				children += self.getChildren(q)
				
		return results + children

	@classmethod
	def getChildren(self,_cat):
		_cat_children = []
		for child in _cat.children:
			for cat in self.locate_primitive(child):
				_cat_children.append(cat)
		#print _cat_children
		return _cat_children


	@classmethod
	def getRoots(self):
		all = Categories.query().fetch()
		#THINK!


#Products DB
class Products(ndb.Model):
	name = ndb.StringProperty(required = True)
	description = ndb.TextProperty()
	popularity = ndb.IntegerProperty()
	category = ndb.KeyProperty(kind = Categories)
	brand = ndb.StringProperty()
	#shopkeeper = ndb.KeyProperty(kind = Shopkeepers)

	@classmethod
	def populate(self):
		products = catalogue.getProducts()
		for product in products:
			#print product
			_name = product[0]
			_brand = product[1]
			_category = Categories.locate_primitive(product[2])[0].key #The numeric key.
			entity = Products(name = _name, brand = _brand, category = _category)
			entity.put()

	@classmethod
	def searchProduct(self,_name,_ease = 70):
		#just find products equal or similar to this
		query = Products.query()

		if _ease > 100:
			_ease = 100

		results = []
		for q in query:
			similarity = fuzz.partial_ratio(q.name,_name)
			if similarity >= _ease:
				results.append((q,similarity))

		return results

	@classmethod
	def searchBrand(self, _name,_ease = 90):
		brand = ''		#The name of the brand. args may have a name similar but not equal. Hence this precaution.
		query = ndb.gql("SELECT DISTINCT brand from Products").fetch()
		#Try printing?
		#print query
		probable_brands = []

		if _ease > 100:
			_ease = 100

		for q in query:
			#First try looking for ratio match.
			similarity = fuzz.partial_ratio(_name.lower(),q.brand.lower())
			#print similarity,_name,q.brand
			if similarity == 100:
				probable_brands = [(q.brand,100)]
				break
			if similarity >= _ease:
				probable_brands.append((q.brand,similarity))

		return probable_brands

	@classmethod
	def searchProductsInCategory(self,_name, _category, _ease = 60):
		#Expects category's name
		_category = Categories.locate(_category,_ease = 60)
		if len(_category) > 0:
			_category = _category[0]
		else:
			return
		

		if not Categories.isLeaf(_category.key):
			return self.searchProductInCategories(_name, Categories.getLeafs(_category.key))

		#Category found in case of leaf, almost perfectly.
		query = Products.query(Products.category == _category.key).fetch()
		
		if _ease > 100:
			_ease = 100

		results = []
		for q in query:
			similarity = fuzz.partial_ratio(q.name,_name)
			if similarity >= _ease:
				results.append((q,similarity))

		#print results
		return results

	@classmethod
	def searchProductInCategories(self,_name,_categories,_ease = 70):
		#Expects categories entity
		_categories_key = []
		for x in _categories: _categories_key.append(x.key)
		query = Products.query(Products.category.IN(_categories_key)).fetch()
		
		if _ease > 100:
			_ease = 100

		results = []
		for q in query:
			similarity = fuzz.token_set_ratio(q.name,_name)
			if similarity >= _ease:
				results.append((q,similarity))

		return results

	@classmethod
	def searchProductInBrand(self,_name,_brand,_ease = 70):
		#Expects consise brand to be known!
		query = Products.query(Products.brand == _brand).fetch()
		
		if _ease > 100:
			_ease = 100

		results = []
		for q in query:
			similarity = fuzz.token_set_ratio(q.name,_name)
			if similarity >= _ease:
				results.append((q,similarity))

		return results		

	@classmethod
	def searchProductInBrands(self,_name,_brands,_ease = 70):
		#Expects brand name to be actual
		query = Products.query(Products.brand.IN(_brands)).fetch()
		
		if _ease > 100:
			_ease = 100

		results = []
		for q in query:
			similarity = fuzz.token_set_ratio(q.name,_name)
			if similarity >= _ease:
				results.append((q,similarity))

		return results		


	@classmethod
	def getAll(self):
		query = self.query().fetch()
		products = []
		for q in query: products.append(q.name + ' B: ' + q.brand + ' C: ' + q.category.urlsafe() + ' K: ' + q.key.urlsafe())
		return products

	@classmethod
	def getProductsInBrand(self,_brand,_ease = 80):
		_brands = self.assure(self.searchBrand(_brand,_ease = 60))
		if len(_brands) > 0:
			_brand = _brands[0]
		else:
			return []
		return Products.query(Products.brand == _brand[0]).fetch()

	@classmethod
	def assure(self,_list):
		#Expected a list of tuples (entity, similarity index). Will sort and return all minus the index
		return sorted(_list, key=lambda tup: tup[1])		

#Setup Users DB. and its methods acting as wrappers
class Users(ndb.Model):
	userid = ndb.StringProperty()
	username = ndb.StringProperty()
	password = ndb.StringProperty()
	visits = ndb.IntegerProperty()

	@classmethod
	def getUserIDs(self):
		users = []
		query = self.query(projection=[Users.userid])
		for user in query: users.append(str(user.userid))
		print users
		return users
		
	@classmethod
	def register(self,_userid,_username,_password):
		print "Registering %s" %_username
		if not _userid in self.getUserIDs():
			user = Users(userid = _userid, username = _username, password = _password)
			user.put()
			return (0,'Success')
		else:
			return (-1,'Userid already exists. Please select a different one')			

class Registration(Handler):
	def get(self):
		print "/registration-get"
		self.response.headers['Content-Type'] = 'text/html'
		self.render("registration.html", userid = "Enter a unique user id", username = "Enter your name")

	def post(self):
		print "/registration-post"
		register_status = (0,'Not begun yet') #If status = 0, so far success. If it goes -1, something's wrong
		self.response.headers['Content-Type'] = 'text/html'
		_userid = self.request.get('userid')
		_username = self.request.get('username')
		_password = self.request.get('password')
		_c_password = self.request.get('c_password')

		_username = str(cgi.escape(_username,quote="True"))
		_userid = str(cgi.escape(_userid,quote="True"))

		#Encrypt the pwd

		#Fix the value of all inputs
		if _password != _c_password:
			register_status = (-1,'The passwords do not match!')

		#Attempt to register. Return value corresponding to success or failure
		if register_status[0] == 0:
			register_status = Users.register(_userid,_username,_password)
			print register_status

		if register_status[0] != 0:
			self.render("registration.html", error = register_status[1], userid = _userid, username = _username)
		else:
			self.redirect("/getusers/")		#Change to homepage.

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
		brands = Products.searchProductsInCategory(_query,_category)
		for b in brands:
			entry = "<li>" + b[0].name + " URL: " + b[0].key.urlsafe() + " BRAND: " + b[0].brand + "</li>"
			self.write(entry)

class FileServer(Handler):
	def get(self):
		print "/css-get"
		print self.request

class MainPage(Handler):
	def get(self):
		print "/-get"
		self.write("Welcome!")

class PrintUsers(Handler):
	def get(self):
		print "/getusers-get"
		queries = Users.getUserIDs()
		for query in queries:
			self.write("<p>%s</p>" % query)

application = webapp2.WSGIApplication([
									('/',MainPage),
									('/products',ProductsPage)
									('/registration',Registration),
									('/getusers/',PrintUsers),
									('/css/',FileServer)
									], debug=True)




#TODO
	#Fetch links,number of products and name of category
	#Implement basic search of sub categories. How? Well its really simple.
		#What i want to do is to simply - fetch all the things that carry the entire text of what we want!
