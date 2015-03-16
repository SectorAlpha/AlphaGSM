#!/usr/bin/python3
'''GET a webpage using http.'''

import http.client
import urllib.request

class Page:

  def __init__(self, servername, path):
    '''This initialize function sets the servername and path'''
    self.set_target(servername, path)

  def set_target(self, servername, path):
    '''This is a utility function that will reset the servername and the path'''
    self.servername = servername
    self.path = path	
					
  def get_as_string(self):
    '''This function provides the webpage as a string'''
    response = urllib.request.urlopen("http://" + self.servername + "/" + self.path)
    html = response.read()
    return html
