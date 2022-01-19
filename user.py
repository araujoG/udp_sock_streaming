import json
from random import random
from types import SimpleNamespace

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
  def get_user_information(id):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['id'] == id:
        return str(user)
    return None

  @staticmethod
  def get_user_by_ip(ip):
    data = json.load(open('users_list.json'))
    for user in data['users']:
      if user['ip'] == ip:
        return str(user)
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

def main():
  user = User('teste', 'admin', f'{int(random() * 100)}')
  user.save()

  user = User('teste', 'admin', f'{int(random() * 100)}')
  user.save()

  print(User.get_user_information(1))

if __name__ == "__main__":
    main()