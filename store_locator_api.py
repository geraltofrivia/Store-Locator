import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote
from datastore import Shops, Categories, Products
from google.appengine.ext import ndb
from collections import defaultdict
from datetime import datetime

package = 'StoreLocator'

class LoginResponseType(messages.Enum):
  NONE = 0
  LOGIN = 1
  NOT_FOUND = 2
  WRONG_PASSWORD = 3

class ShopkeeperRequestAuthentication(messages.Message):
  email = messages.StringField(1, required=True)
  password = messages.StringField(2, required=True)

class ShopkeeperField(messages.Message):
  fname = messages.StringField(1)
  lname = messages.StringField(2)
  email = messages.StringField(3)
  id = messages.IntegerField(4)
  mobile = messages.IntegerField(5)
  shop_name = messages.StringField(6)
  shop_address = messages.StringField(7)

class ShopkeeperResponseAuthentication(messages.Message):
  status = messages.EnumField(LoginResponseType, 1)
  shopkeeperInformation = messages.MessageField(ShopkeeperField, 2)

class ShopkeeperReponseBoolean(messages.Message):
  status = messages.BooleanField(1)
  id = messages.IntegerField(2)

class Category(messages.Message):
  _id = messages.IntegerField(1)
  name = messages.StringField(2)
  parent_id = messages.IntegerField(3)
  deleted = messages.IntegerField(4)
  timestamp = messages.StringField(5)

class CategoryList(messages.Message):
  categories = messages.MessageField(Category, 1, repeated=True)
  latestTimestamp = messages.StringField(2)

class Product(messages.Message):
  _id = messages.IntegerField(1)
  name = messages.StringField(2)
  description = messages.StringField(3)
  popularity = messages.IntegerField(4)
  category = messages.IntegerField(5)
  brand = messages.StringField(6)

class ProductList(messages.Message):
  products = messages.MessageField(Product, 1, repeated=True)

def datetime_to_string(datetime_object):
  '''Converts a datetime object to a
  timestamp string in the format:
  2013-09-23 23:23:12.123456'''
  return datetime_object.isoformat(sep=' ')

def parse_timestamp(timestamp):
  '''Parses a timestamp string.
  Supports two formats, examples:
  In second precision
  >>> parse_timestamp("2013-09-29 13:21:42")
  datetime object
  Or in fractional second precision (shown in microseconds)
  >>> parse_timestamp("2013-09-29 13:21:42.123456")
  datetime object
  Returns None on failure to parse
  >>> parse_timestamp("2013-09-22")
  None
  '''
  result = None
  try:
      # Microseconds
      result = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
  except ValueError:
      pass

  try:
      # Seconds
      result = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
  except ValueError:
      pass

  return result

@endpoints.api(name='storelocator', version='v1', allowed_client_ids=['148827402385-m8tetu1vf8o2snnjtii5s2p4dif7e3uu.apps.googleusercontent.com'])
class StoreLocatorAPI(remote.Service):

  @endpoints.method(ShopkeeperRequestAuthentication, ShopkeeperResponseAuthentication,
                    path="login", http_method='POST',
                    name='greetings.shopkeeperAuthentication')
  def check_shopkeeper_authentication(self, request):
    try:
      statusMessage = LoginResponseType.NONE
      query = Shops.query(Shops.email == request.email).fetch() 
      if len(query) == 0:
        statusMessage = LoginResponseType.NOT_FOUND
      elif query[0].password != request.password:
        statusMessage = LoginResponseType.WRONG_PASSWORD
      else:
        statusMessage = LoginResponseType.LOGIN
        shopkeeperField = ShopkeeperField(fname = query[0].fname,
                              lname = query[0].lname,
                              id = query[0].key.id(),
                              mobile = query[0].mobile,
                              shop_name = query[0].shop_name,
                              shop_address = query[0].shop_address,
                              email = query[0].email)
        return ShopkeeperResponseAuthentication(status = statusMessage, shopkeeperInformation = shopkeeperField)
      return ShopkeeperResponseAuthentication(status=statusMessage)
    except(TypeError):
      raise endpoints.NotFoundException('Error in the input format')

  @endpoints.method(ShopkeeperField, ShopkeeperReponseBoolean,
                    path="shopkeeper", http_method='POST',
                    name='greetings.shopkeeperProfileUpdate')
  def shopkeeper_profile_update(self, request):
    currentShopkeeper = ndb.Key("Shops", request.id).get()
    currentShopkeeper.fname = request.fname
    currentShopkeeper.lname = request.lname
    currentShopkeeper.mobile = request.mobile
    currentShopkeeper.shop_name = request.shop_name
    currentShopkeeper.shop_address = request.shop_address
    currentShopkeeper.put();
    return ShopkeeperReponseBoolean(status=True)

  SHOPKEEPER_REQUEST = endpoints.ResourceContainer(message_types.VoidMessage,
      id=messages.IntegerField(1))
  @endpoints.method(SHOPKEEPER_REQUEST, ShopkeeperField,
                    path="shopkeeper", http_method='GET',
                    name='greetings.getShopkeeperProfile')
  def get_shopkeeper_profile(self, request):
    currentShopkeeper = ndb.Key("Shops", request.id).get()
    return ShopkeeperField(fname=currentShopkeeper.fname,
                    id=request.id,
                    lname=currentShopkeeper.lname,
                    mobile=currentShopkeeper.mobile,
                    email=currentShopkeeper.email,
                    shop_address=currentShopkeeper.shop_address,
                    shop_name=currentShopkeeper.shop_name)

  @endpoints.method(ShopkeeperRequestAuthentication, ShopkeeperReponseBoolean,
                    path="register", http_method='PUT',
                    name='greetings.register')
  def register_shopkeeper(self, request):
      if len(Shops.query(Shops.email == request.email).fetch()) == 0:
        id = Shops(email=request.email, password=request.password).put().get().key.id()
        return ShopkeeperReponseBoolean(status=True, id=id)
      else:
        return ShopkeeperReponseBoolean(status=False)

  LIST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    showDeleted=messages.BooleanField(2, default=False),
    timestampMin=messages.StringField(3))

  @endpoints.method(LIST_REQUEST, CategoryList,
                    path="categories", http_method='GET',
                    name='greetings.get_categories')
  def get_all_categories(self, request):
      categoryList = []
      categoryHash = defaultdict(int)
      q = Categories.query()
      q.order(Categories.timestamp)

      if not request.showDeleted:
        q = q.filter(Categories.deleted == False)
      if request.timestampMin is not None and parse_timestamp(request.timestampMin) is not None:
        q = q.filter(Categories.timestamp > parse_timestamp(request.timestampMin))

      result = q.fetch()
      
      index = 0
      latest_time = None
      for category in result:
        ts = category.timestamp
        if latest_time is None:
          latest_time = ts
        else:
          delta = ts - latest_time
          if delta.total_seconds() > 0:
            latest_time = ts
        categoryList.append(Category(_id=category.key.id(), name=category.name,
          deleted=category.deleted, timestamp=datetime_to_string(ts)))
        categoryHash[category.name] = [index, category.key.id()]
        index+=1
      for category in result:
        for subcategory in category.children:
          categoryList[categoryHash[subcategory][0]].parent_id = categoryHash[category.name][1]
      if latest_time is None:
        if request.timestampMin is not None and parse_timestamp(request.timestampMin) is not None:
          latest_time = datetime.now()
        else:
          latest_time = datetime(1970, 1, 1, 0, 0)
      return CategoryList(categories=categoryList, 
        latestTimestamp=datetime_to_string(latest_time))

  PRODUCT_SEARCH_REQUEST = endpoints.ResourceContainer(
    name=messages.StringField(1),
    parent_id=messages.IntegerField(2))
  @endpoints.method(PRODUCT_SEARCH_REQUEST, ProductList,
                    path="search", http_method='GET',
                    name='greetings.search_product')
  def search_product(self, request):
    productList = []
    if request.name:
      result = Products.searchProduct(request.name)
      for p in result:
        productList.append(Product(
          _id=p[0].key.id(),
          name=p[0].name,
          description=p[0].description,
          popularity=p[0].popularity,
          category=p[0].category.id(),
          brand=p[0].brand
          ))
    else:
      currentCategory = ndb.Key("Categories", request.parent_id).get()
      result = Products.query(Products.category == currentCategory.key).fetch()
      for p in result:
        productList.append(Product(
          _id=p.key.id(),
          name=p.name,
          description=p.description,
          popularity=p.popularity,
          category=p.category.id(),
          brand=p.brand
          ))
    return ProductList(products=productList)
APPLICATION = endpoints.api_server([StoreLocatorAPI])