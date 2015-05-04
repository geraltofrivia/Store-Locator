import datetime

from google.appengine.ext import ndb 
from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError

import utils
import catalogue					#TO populate the Categories DB
from fuzzywuzzy import fuzz 		#For better search

#Categories DB
class Categories(ndb.Model):
	name = ndb.StringProperty(required = True)
	children = ndb.StringProperty(repeated = True)

	@classmethod
	def populate(self):
		query = Categories.query().fetch()
		if len(query) > 0:
			return False

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
	def fetch_by_id(self,category_id,get_children = False):
		query = Categories.query().fetch()
		results = []
		#print "productsdb: fetch_by_id: ", product_key
		for q in query:
			if str(q.key.id()) == str(category_id):
				results.append(q)
		if get_children:
			results += self.getChildren(results[0])

		return results

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
		children = utils.remove_similarity(self.getChildren(category))
		#print "categoryb: getleafs: children are ", children
		while True:
			all_leaves = True
			new_list = []
			for child in children:
				if not self.isLeaf(child.key):
					all_leaves = False
					new_list += utils.remove_similarity(self.getChildren(child))
				else:
					new_list.append(child)
			children = new_list
			if all_leaves:
				break

		return children

	@classmethod
	def search(self,_name,_getchild = False,_ease = 70):
		#Get a list of categories which have the argument string in it.
		#query = self.locate(_name,_getchild = True)
		results = []
		children = []
		query = Categories.query().fetch()
		for q in query:
			similarity = fuzz.partial_ratio(_name.lower(), q.name.lower())
			print similarity, q.name, _name
			if similarity >= _ease:
				results.append((q,similarity))

		if _getchild:
			for q in results:
				children += self.getChildren(q[0])

		return results + children

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
			#print similarity, q.name, _name
			if similarity == 100:
				results = [(q,100)]
				break
			if similarity >= _ease:
				results.append((q,similarity))

		if _getchild:
			for q in results:
				children += self.getChildren(q[0])
				
		return results + children

	@classmethod
	def getChildren(self,_cat):
		_cat_children = []
		for child in _cat.children:
			for cat in self.locate_primitive(child):
				_cat_children.append((cat,0))
		print "GET CHILDREN- ",_cat_children
		return _cat_children

	@classmethod
	def getRoots(self):
		root=[]
		children=[]
		all1 = ndb.gql("SELECT * FROM Categories").fetch()
		#Made a copy of all categories
		root = all1[:]
		for q in all1:
			children = self.getChildren(q)
			for child in children:
				for r in root:
					if r.key == child[0].key:
						#print "REMOVING", r.name
						root.remove(r)
		#print len(all1), len(root)
		return root

	@classmethod
	def getAllLeaves(self):
		leaves = ndb.gql("SELECT * from Categories").fetch()
		for element in leaves:
			if not self.isLeaf(element.key):
				leaves.remove(element)
		return leaves
		

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
		query = Products.query().fetch()
		if len(query) > 0:
			return False

		products = catalogue.getProducts()
		for product in products:
			#print product
			_name = product[0]
			_brand = product[1]
			_category = Categories.locate_primitive(product[2])[0].key #The numeric key.
			entity = Products(name = _name, brand = _brand, category = _category)
			entity.put()


	@classmethod
	def fetch_by_id(self,product_key):
		query = Products.query().fetch()
		#print "productsdb: fetch_by_id: ", product_key
		for q in query:
			if str(q.key.id()) == str(product_key):
				print "productsdb: fetch_by_id: foundproduct", q
				return q
		return None

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
	def searchBrand(self, _name,_ease = 85):
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
	def getProductsInBrand(self,_brand):
		_brands = utils.sort(self.searchBrand(_brand,_ease = 60))
		if len(_brands) > 0:
			_brand = _brands[0]
		else:
			return []
		return Products.query(Products.brand == _brand[0]).fetch()

	@classmethod
	def getProductsInBrands(self,_brands_list):
		_products = []
		for _brand in _brands_list:
			_products += self.getProductsInBrand(_brand)
		return _products
	

	@classmethod
	def getProductsInCategory(self,_category):
		#Expects entity
		print "productdb: getProductsInCategory: ", _category
		_products = Products.query(Products.category == _category.key).fetch()
		return _products

	@classmethod
	def getProductsInCategories(self,_category_list):
		#Expects entity
		for c in _category_list[:]:
			if not Categories.isLeaf(c.key):
				_category_list += Categories.getLeafs(c.key)

		_products = []
		for _category in _category_list:
			_products += self.getProductsInCategory(_category)
		return _products

	@classmethod
	def getCategoriesForProducts(self,_products):
		#Expects products entity.
		#Returns category entity.
		distinct_category_keys = []
		for _product in _products:
			if _product.category not in distinct_category_keys:
				distinct_category_keys.append(_product.category)
		#print "PRODUCT LENGTH: ", len(_products)
		#print distinct_category_keys

		#Now to find the category entities
		distinct_categories = []
		for keys in distinct_category_keys:
			distinct_categories.append(keys.get())
		return distinct_categories

	@classmethod
	def filterProductInCategory(self,product_list,category):
		#Expects a list of valid product and a category id.
		result = []
		for p in product_list:
			print "productdb: filter: ",p.category, category.key
			if p.category == category.key:
				result.append(p)
		return result

	@classmethod
	def filterProductInCategories(self,product_list,categories):
		result = []
		for c in categories:
			a = utils.add_similarity(self.filterProductInCategory(product_list,c))
			print a
			b = utils.add_similarity(result)
			result = utils.remove_similarity(utils.join(a,b,_distinct = True))
		return result


#Setup Users DB. and its methods acting as wrappers
class Users(ndb.Model):
	fname = ndb.StringProperty()
	lname = ndb.StringProperty()
	email = ndb.StringProperty()
	password = ndb.StringProperty()
	active_sessions = ndb.PickleProperty(repeated = True)
	shopping_list = ndb.KeyProperty(kind = Products,repeated = True)
	shopping_list_archived = ndb.KeyProperty(kind = Products,repeated = True)
	location = ndb.GeoPtProperty()


	@classmethod
	def getUserIDs(self):
		users = []
		query = self.query(projection=[Users.userid])
		for user in query: users.append(str(user.userid))
		print users
		return users
		
	@classmethod
	def register(self,_fname,_lname,_email,_password):
		#print "Registering %s" %_username
		query = Users.query(Users.email == _email).fetch()
		if len(query) > 0:
			return (-1,'There already exists an account with this email ID.')			
		else:
			user = Users(fname = _fname, lname = _lname, email=_email, password = _password)
			key = user.put()
			return (key.urlsafe(),'Registered Successfully.')

	@classmethod
	def update_info(self,_fname,_lname,_email,_user):
		#Expects html escaped variables and valid user
		if _fname != '-1':
			_user.fname = _fname
		if _lname != '-1':
			_user.lname = _lname
		if _email != '-1':
			_user.email = _email
			#TODO set a verification process here!
		_user.put()
		return

	@classmethod
	def update_password(self,_pwd,_nwpwd,_user):
		if _user.password == _pwd:
			print "userdb: changing password: ", _user, _nwpwd
			_user.password = _nwpwd
			_user.put()
			return True
		else:
			return False

	@classmethod
	def checkValidSession(self,_user,_session):
		#First check for the user
		print "Checking for user based on userid", _user
		users = Users.query()
		user = None
		for u in users:
			if str(u.key.id()) == _user:
				user = u
				break

		print user
		result = -1
		if not user:
			return result

		#print "IN CHECK VALID SESSION: ", user
		for session in user.active_sessions:
			#print session[0], _session
			if session[0] == _session:
				if utils.time_difference(session[1],str(datetime.datetime.now()),7) :
					result = user
		return result

	@classmethod
	def createSessionID(self,_user):
		#Expects real user entity
		time = str(datetime.datetime.now())
		string = utils.encrypt(utils.generate_string())
		_user.active_sessions = _user.active_sessions + [(string,time)]
		_user.put()
		#print "Users-createSessionID: Created new ID for ", _user.email
		return (string,time)
			
	@classmethod
	def login(self,_email,_password):
		session = (-1,'Does not exist')
		_user = -1
		query = Users.query(Users.email == _email).fetch()
		for q in query:
			if q.password == _password:
				_user = q
				session = self.createSessionID(q)

		print "userdb: login: found user: ",_user

		if not _user == -1:
			return (session[0],_user)
		else:
			print "userdb: login: UNSUCCESSFUL"
			return (-1,-1)

	@classmethod
	def logout(self,_user,_session):
		print "userdb: logout: Checking for user based on userid", _user
		users = Users.query()
		user = None
		for u in users:
			if str(u.key.id()) == _user:
				user = u
				break

		print user
		result = -1
		if not user:
			return result

		for session in user.active_sessions[:]:
			print session[0], _session
			if session[0] == _session:
				remaining_session  = []
				for s in user.active_sessions:
					if not s == session:
						remaining_session.append(s)
				user.active_sessions = remaining_session
				user.put()
				result = user
				break

		return result

	@classmethod
	def add_product(self,_product,_user_key):
		#Expects a user key here. Not just name
		#Expects a product entity key here. Will check nonetheless
		print "userdb: add_product: ",_product, _user_key
		product = Products.fetch_by_id(_product)
		user = Users.get_by_id(_user_key)
		print "userdb: add_product checking entries", product, user
		if product and user:	
			if product.key in user.shopping_list:
				print "userdb: add_product duplicate entry", product.key, user.shopping_list
				return False
			user.shopping_list = user.shopping_list + [product.key]
			user.put()
			#print "shopdb: add_product: user", user
			#print "shopdb: add_product: product", str(product.key.id)
			return True
		return False

	@classmethod
	def remove_product(self,_product,_user_key):
		#Expects a user key & product key
		print "userdb: remove_product: ", _product,_user_key
		if self.check_product(_product,_user_key,might_as_well_remove_it = True):
			print "userdb: remove_product: FOUND", _product,_user_key
			return True
		return False

	@classmethod
	def check_product(self,_product,_user,might_as_well_remove_it = False):
		user = Users.get_by_id(_user)
		if user:
			print "userdb: check_product: Finding product in list", _product,user.shopping_list
			for key in user.shopping_list:
				if str(key.id()) == _product:
					print "userdb: check_product: product found"
					if might_as_well_remove_it:
						user.shopping_list.remove(key)
						user.shopping_list_archived.append(key)
						user.put()
					return True
		return False

	@classmethod
	def get_products(self,_user):
		#Expects user key
		#Will return a list of product entities
		user = Users.get_by_id(_user)
		if user:
			products = []
			if not user.shopping_list:
				return products
			
			for k in user.shopping_list:
				products.append(Products.get_by_id(k))

	@classmethod
	def updateLocation(self,_latitude,_longitude,_user):
		#Expects float lat and long. And expects valid key id

		if _user:
			#If no shop found, shop object is nonetype
			_user.location = ndb.GeoPt(_latitude,_longitude)
			_user.put()
			return True

		return False


#Shopkeeper
class Shops(ndb.Model):
	fname = ndb.StringProperty()
	lname = ndb.StringProperty()
	email = ndb.StringProperty(required = True)
	password = ndb.StringProperty(required = True)
	mobile = ndb.IntegerProperty()
	shop_name = ndb.StringProperty()
	shop_address = ndb.StringProperty()
	location = ndb.GeoPtProperty()
	inventory =  ndb.KeyProperty(kind = Products, repeated = True)
	inventory_archived =  ndb.KeyProperty(kind = Products, repeated = True)
	active_sessions = ndb.PickleProperty(repeated = True)
	open = ndb.BooleanProperty()
	verified = ndb.BooleanProperty()

	#Register function
	@classmethod
	def register(self,_email,_fname,_lname,_password,_mobile,_shop_name,_shop_address):
		#Assumes verified values
		if self.shopExists(_shop_name,_email):
			
			entity = Shops(fname = _fname, lname = _lname, email = _email, password = _password, mobile = _mobile, shop_name = _shop_name, shop_address = _shop_address, verified = False)
			entity.put()
			Verification.new_pending_shop(entity)
			print "shopdb: register: ", entity
			return (0,'Success')
		else:
			print "User already exists"
			return (-1,'This shop already exists')

	@classmethod
	def fetch_by_id(self, id):
		query = Shops.query()
		for q in query:
			if str(q.key.id()) == str(id):
				return q

	@classmethod
	def get_shop_by_url(self, url):
		rev_key = ndb.Key(urlsafe=urlString)
		return rev_key.get()

	@classmethod
	def open_shop(self,_shop):
		_shop.open = True
		_shop.put()

	@classmethod
	def close_shop(self,_shop):
		_shop.open = False
		_shop.put()

	@classmethod
	def get_open_shops(self):
		query = Shops.query(Shops.open == True).fetch()
		return query

	@classmethod
	def get_open_shops_from_list(self,shops):
		results = []
		for q in shops:
			if q.__class__ == Shops.query().get().__class__:
				if q.open:
					results.append(q)
		return q

	@classmethod
	def update_info(self,_fname, _lname, _email, _mobile, _shop_name, _shop_address, _shop):
		#Expects html escaped variables and valid user
		if not _shop:
			return

		if _fname != '-1':
			_shop.fname = _fname
		if _lname != '-1':
			_shop.lname = _lname
		if _email != '-1':
			_shop.email = _email
		if _mobile != '-1':
			_shop.mobile = _mobile
		if _shop_name != '-1':
			_shop.shop_name = _shop_name
		if _shop_address != '-1':
			_shop.shop_address = _shop_address

		_shop.put()
		return

	@classmethod
	def update_password(self,_pwd,_nwpwd,_shop):
		if _shop.password == _pwd:
			print "shopdb: changing password: ", _shop, _nwpwd
			_shop.password = _nwpwd
			_shop.put()
			return True
		else :
		    return False	


	@classmethod
	def shopExists(self,_shop_name,_email,_need_user = False):
		#If need user and user not exist then will return nonetype!
		query = Shops.query(Shops.email == _email).fetch()
		#print "shopdb: shopexits: query is ", query
		if len(query) > 0:
			if _need_user:
				return None
			return False
		
		print "shopdb: shopexists: no user found", _email
		if _need_user:
			return None
		return True

	@classmethod
	def login(self,_email,_password):
		session = (-1,'Does not exist')
		_shop = -1
		query = Shops.query(Shops.email == _email).fetch()
		for q in query:
			if q.password == _password:
				_shop = q
				session = self.createSessionID(q)

		print "LOGIN FOUND SHOP: ",_shop

		if not _shop == -1:
			return (session[0],_shop)
		else:
			print "Shops-login UNSUCCESSFUL"
			return (-1,-1)

	@classmethod
	def createSessionID(self,_shop):
		#Expects real shopkeeper entity
		time = str(datetime.datetime.now())
		print "shop: createsessionid: creating sessionid for ", _shop.email
		string = utils.encrypt(utils.generate_string())
		_shop.active_sessions = _shop.active_sessions + [(string,time)]
		_shop.put()
		return (string,time)

	@classmethod
	def checkValidSession(self,_shop,_session):
		print "Checking for user based on userid", _shop
		shops = Shops.query()

		shop = None
		for s in shops:
			if str(s.key.id()) == _shop:
				shop = s
				break

		print "shopdb: checkvalid session: shop found:", shop
		result = -1
		if not shop:
			return result

		print "checkvalidsession: ", shop.active_sessions
		for session in shop.active_sessions:
			#print session[0], _session
			if session[0] == _session:
				if utils.time_difference(session[1],str(datetime.datetime.now()),7) :
					result = shop
		return result

	@classmethod
	def updateLocation(self,_latitude,_longitude,_shop_key):
		#Expects float lat and long. And expects valid key id
		shop = Shops.get_by_id(_shop_key)
		print "shopdb: updatelocation: found shop", shop

		if shop:
			#If no shop found, shop object is nonetype
			shop.location = ndb.GeoPt(_latitude,_longitude)
			shop.put()
			return True

		return False

	@classmethod
	def add_product(self,_product,_shop_key):
		#Expects a user key here. Not just name
		#Expects a product entity key here. Will check nonetheless
		print "shopdb: add_product: ",_product, _shop_key
		product = Products.fetch_by_id(_product)
		shop = Shops.get_by_id(_shop_key)
		print "shopdb: add_product checking entries", product, shop
		if product and shop:	
			if product.key in shop.inventory:
				print "shopdb: add_product duplicate entry", product.key, shop.inventory
				return False
			shop.inventory = shop.inventory + [product.key]
			shop.put()
			#print "shopdb: add_product: user", user
			#print "shopdb: add_product: product", str(product.key.id)
			return True
		return False

	@classmethod
	def remove_product(self,_product,_shop_key):
		#Expects a user key & product key
		print "shopdb: remove_product: ", _product,_shop_key
		if self.check_product(_product,_shop_key,might_as_well_remove_it = True):
			print "shopdb: remove_product: FOUND", _product,_shop_key
			return True
		return False

	@classmethod
	def check_product(self,_product,_shop,might_as_well_remove_it = False):
		shop = Shops.get_by_id(_shop)
		if shop:
			print "shopdb: check_product: Finding product in list", _product,shop.inventory
			for key in shop.inventory:
				if str(key.id()) == _product:
					print "shopdb: check_product: product found"
					if might_as_well_remove_it:
						shop.inventory.remove(key)
						shop.inventory_archived.append(key)
						shop.put()
					return True
		return False

	@classmethod
	def get_products(self,_shop):
		#Expects user key
		#Will return a list of product entities
		shop = Shops.get_by_id(_shop)
		if shop:
			products = []
			if not shop.inventory:
				return products
			
			for k in shop.inventory:
				products.append(Products.get_by_id(k))

	@classmethod
	def match_products(self,_product_list,_shop):
		#Expects a valid shop.
		percent = 0
		if _shop.__class__ ==  Shops.query().get().__class__:
			#It actually is a shop product.
			match = 0.0
			#print "shopdb: match_products: about to match: ", _product_list _shop.inventory
			for p in _product_list:
				#print "shopdb: match_products: about to look for: ", p
				for i in _shop.inventory:
					if str(p) == str(i.id()):
						match += 1
			percent =  match*100/float(len(_product_list))
		return percent


	@classmethod
	def logout(self,_shop,_session):
		print "shopdb: logout: Checking for user based on userid", _shop
		shops = Shops.query()
		shop = None
		for sp in shops:
			if str(sp.key.id()) == _shop:
				shop = sp
				break

		print shop
		result = -1
		if not shop:
			return result

		for session in shop.active_sessions[:]:
			print session[0], _session
			if session[0] == _session:
				remaining_session  = []
				for s in shop.active_sessions:
					if not s == session:
						remaining_session.append(s)
				shop.active_sessions = remaining_session
				shop.put()
				result = shop
				break

		return result

class Verification(ndb.Model):
	shop = ndb.KeyProperty(kind= Shops, required = True)
	code = ndb.StringProperty(required = True)

	@classmethod
	def verify_shop(self,urlstring):
		query = Verification.query().fetch()
		for q in query:
			if str(q.code) == str(urlstring):
				shop = q.shop.get()	
				print "DEBUG ", shop
				shop.verified = True
				shop.put()
				q.key.delete()

	@classmethod
	def new_pending_shop(self,_shop):
		#Expects valid shop entity.
		_code = utils.generate_string(size= 20)
		entity = Verification(shop = _shop.key, code = _code)
		entity.put()
		utils.email_verification(_shop,_code)


