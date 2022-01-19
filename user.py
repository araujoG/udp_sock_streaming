import json
from random import random
from types import SimpleNamespace
from unicodedata import name

class User:
  def __init__(self, name, type, ip):
    self.id = User.get_next_id()
    self.ip = ip
    self.name = name
    self.type = type

  def __str__(self):
    return f"{self.id} {self.name} {self.type} {self.ip}"
   
  def __dict__(self):
    return {
      'id': self.id,
      'name': self.name,
      'type': self.type,
      'ip': self.ip
    }

  def save(self):
    data = json.load(open('users_list.json'))
    data['users'].append(self.__dict__())
    json.dump(data, open('users_list.json', 'w'))

  def get_type(self):
    if self.type == 0:
      return 'Convidade'
    return "Premium"

  @staticmethod
  def show_group(id):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['id'] == id:
        users = ""
        for u in user['group']:
          for group_user in data['users']:
            if group_user['ip'] == u:
              users += f"{group_user['id']} "

    users = users.rstrip()
    return users


  @staticmethod
  def add_group_to_user(id):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['id'] == id:
        user_index = next((index for (index, d) in enumerate(data['users']) if d["id"] == id), None)
        print(user_index)
        data['users'][user_index]['group'] = [user['ip']]
        json.dump(data, open('users_list.json', 'w'))
    return None

  @staticmethod
  def get_user_information(id):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['id'] == id:
        return f"{user['id']} {user['name']} {user['type']} {user['ip']}"
    return None

  @staticmethod
  def get_user_by_ip(ip):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['ip'] == ip:
        return f"{user['id']} {user['name']} {user['type']} {user['ip']}"
    return None
  
  @staticmethod
  def get_next_id():
    data = json.load(open('users_list.json'))
    if data['users'] == []:
      return 1
    return data['users'][-1]['id'] + 1

  @staticmethod
  def remove_by_ip(ip):
    data = json.load(open('users_list.json'))
    data['users'] = [user for user in data['users'] if user['ip'] != ip]
    json.dump(data, open('users_list.json', 'w'))

  @staticmethod
  def fromDict(d):
    return User(d['name'], d['type'], d['ip'])

def main():
  user = User('teste', 'admin', f'{int(random() * 100)}')
  user.save()

  user = User('teste', 'admin', f'{int(random() * 100)}')
  user.save()

  print(User.get_user_information(1))

if __name__ == "__main__":
    main()