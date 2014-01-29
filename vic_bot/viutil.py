#!/usr/bin/python
# -*- coding: utf-8  -*-
import sys, os
sys.path.append(os.environ['HOME'] + '/core')

import pywikibot
import urllib
import re
import htmlentitydefs

"""
  vi-util.py
  by Eusebius and Dschwen
  
  utility methods for the processing of Valued Images.
  
  TODO: use SQL instead of API
  
  Methods available:
  
  unescape_charref
  replace_entities
  unescape
  getScope                  retrieves a scope from either a VI candidate page, a VI image page or a VI-former image page.
  getVIfromVIC              retrives a VI image page name from the VI candidate page
  BROKEN!: getLeastReplaggedCommons  returns the least replagged Commons replica, to be used as a host in a MySQLdb connection
"""

def unescape_charref(ref) :
  name = ref[2:-1]
  base = 10
  if name.startswith("x") :
    name = name[1:]
    base = 16
  return unichr(int(name, base))

def replace_entities(match) :
  ent = match.group()
  if ent[1] == "#":
    return unescape_charref(ent)

  repl = htmlentitydefs.name2codepoint.get(ent[1:-1])
  if repl is not None :
    repl = unichr(repl)
  else :
    repl = ent
  return repl

def unescape(data) : 
  return re.sub(r"&#?[A-Za-z0-9]+?;", replace_entities, data)

def getScope(page):
  """
    Retrieves the scope (with links and everything) of either a VI candidate page, a VI image page or a VI-former image page.
    Returns either a unicode string or False (silently) in case of error.
    
    Arguments:
      page: The Page object from which the scope should be extracted. If it is a redirection, the redirection is silently followed.
  """
  
  if page.isRedirectPage():
    page = page.getRedirectTarget()
  
  if page.isImage():
    #It should be either a VI or a VI-former
    
    try:
      text = page.get()
    except:
      return False
    
    templates = page.templatesWithParams()
    for template in templates:
      if template[0].find(u'VI') == 0 or template[0].find(u'Valued image') == 0:
        return template[1][0]
    return False
    
  else:
    #It should be a VI candidate page
    if not page.title().startswith(u"Commons:Valued image candidates"):
      return False
    
    try:
      text = page.get()
    except:
      return False
    
    templates = page.templatesWithParams()
    for template in templates:
      if template[0].find(u'VIC') == 0:
        for param in template[1]:
          if param.find(u'scope') == 0:
            scope = param[6:len(param)]
            scope = scope.lstrip().rstrip()
            return scope
    return False

def getVIfromVIC(vicPage):
  """
    Retrieves a VI image page name from a VIC page
    Returns either a string or False (silently) in case of error.
    
    Arguments:
      vicPage: The VIC Page object
  """
    
  try:
    text = vicPage.get()
  except:
    return False

  templates = vicPage.templatesWithParams()
  for template in templates:
    if template[0].find(u'VIC') == 0:
      for param in template[1]:
        if param.find(u'image') == 0:
          imageName = param[6:len(param)]
          imageName = imageName.lstrip().rstrip()
          return u"File:" + imageName
  return False

# Returns the name of the least replagged Commons replica
def getLeastReplaggedCommons():
  """
    Returns the name of the least replagged Commons replica among s1, s2 and s3
  """
  return "commonswiki-p.rrdb.toolserver.org"
  # broken:
  #return urllib.urlopen("http://toolserver.org/~eusebius/leastreplag").readline()
