#!/usr/bin/python
# -*- coding: utf-8  -*-
import sys, os
sys.path.append(os.environ['HOME'] + '/core')

import pywikibot
import pagegenerators
import catlib
import traceback
from operator import itemgetter
import viutil

"""
  vi-maintenance.py
  by Eusebius
  
  Usage: python vi-maintenance.py [-debug]
  
  Attention: this script is currently very slow. It shouldn't be run often, and always nicely.
  Hints for improving efficiency: 1. rely on SQL rather than API, 2. generate a list of VIs once and for all
  
  What this script does:
  1. Adds in "Valued images/Recently promoted" VIs that are not already in a "by topic" gallery
  2. Removes non-VIs (demoted and renamed VIs) from the "Valued images by topic" galleries
"""

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}

class EuseBot:

  def __init__(self, debug):
    """
    Constructor. Parameters:
      * debug     - If True, doesn't do any real changes, but only shows
                    what would have been changed.
    """
    self.debug = debug

  # Give up if replag on main server is too high
  def put(self, page, text):
    page.put(text, maxTries=20)

  def run(self):
    # Set the edit summary message
    pywikibot.setAction(u'Preparing newly promoted [[COM:VI|Valued Images]] for sorting')
    site = pywikibot.getSite()
    rootCat = catlib.Category(site,'Category:Promoted valued image candidates')
    
    #All promoted VICs
    vics = pagegenerators.CategorizedPageGenerator(rootCat, recurse=False)
    
    #List of VIs corresponding to the promoted VICs
    vis = []
    
    #Available VI gallery prefixes
    #prefixes = [u'Activities', u'Animals', u'Concepts and ideas', u'Events', u'Food and drink', u'Historical', u'Microscopic', u'Natural phenomena', u'Objects', u'People', u'Places', u'Plants', u'Science', u'Works of art', u'Recently promoted', ]
    
    #Output text
    outputText = ""
    
    #Processed VIs
    viCounter = 0
    
    for page in vics:
      #find out whether it is categorized already, or in "Recently promoted"
      scope = viutil.getScope(page)
      imageFileName = viutil.getVIfromVIC(page)
      
      if scope == False:
        pywikibot.output(u"Error: could not retrieve the scope for: " + page.title())
        continue
      if imageFileName == False:
        pywikibot.output(u"Error: could not retrieve the image file name for: " + page.title())
        sys.exit(0)
        continue
      
      imagePage = pywikibot.ImagePage(site, imageFileName)
      vis.append(imagePage)
      
      toBeConsidered = True
      referers = imagePage.usingPages()
      for referer in referers:
        if not toBeConsidered:
          break
        if referer.title().startswith(u'Commons:Valued images by topic') or referer.title().startswith(u'Commons:Valued images/Recently promoted'):
          toBeConsidered = False
          break
      if toBeConsidered:
        #Only executed if the image is not linked already
        outputText += u'\nFile:' + imageName + u'|' + scope
        viCounter += 1
    
    #Number of new VIs
    pywikibot.output(u"%i new valued images found." % viCounter)
    
    #Opening the "recently promoted" page
    outputPage = pywikibot.Page(site, u'Commons:Valued images/Recently promoted')
    try:
      currentOutputText = outputPage.get()
    except pywikibot.NoPage:
      pywikibot.output(u"Page %s does not exist; skipping." % outputPage.aslink())
      return
    except pywikibot.IsRedirectPage:
      pywikibot.output(u"Page %s is a redirect; skipping." % outputPage.aslink())
    
    #Updating the text by adding the new VIs
    endOfGal = currentOutputText.rfind(u'\n</gallery>')
    if endOfGal < 0:
      pywikibot.output(u"Gallery on page %s is malformed; skipping." % outputPage.aslink())
      sys.exit(1)
    newOutputText = currentOutputText[:endOfGal]
    newOutputText += outputText
    newOutputText += currentOutputText[endOfGal:]
    
    if not self.debug:
      try:
        # Save the page
        self.put(outputPage, newOutputText)
      except pywikibot.LockedPage:
        pywikibot.output(u"Page %s is locked; skipping." % outputPage.aslink())
      except pywikibot.EditConflict:
        pywikibot.output(u'Skipping %s because of edit conflict' % (outputPage.title()))
      except pywikibot.SpamfilterError, error:
        pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (outputPage.title(), error.url))
    oldtext = outputPage.get()
    if (oldtext != newOutputText):
      pywikibot.output(u"*** %s ***" % outputPage.title())
      pywikibot.showDiff(oldtext, newOutputText)
    
    #Now check that only promoted VIs are in the galleries (in fact, images tagged with VI)
    pywikibot.setAction(u'Removing demoted and renamed [[COM:VI|Valued Images]] from the galleries')
    galleries = pagegenerators.PrefixingPageGenerator("Commons:Valued images by topic")
    #viTemplate = pywikibot.Page(site, "Template:VI")
    for gallery in galleries:
      try:
        images = gallery.imagelinks()
        for image in images:
          #templates = image.templates()
          #if ("Vi" not in templates) and ("VI" not in templates) and ("Valued images" not in templates):
          if image not in vis:
            pywikibot.output(u'*** Images removed from the galleries: ' + image.title())
            text = gallery.get()
            outputText = text
            linestart = text.find(image.title())
            if (linestart == -1):
              pywikibot.output(u"Image " + image.title() + "not found in " + gallery.title())
            else:
              lineend = text.find(u"\n", linestart)
              if (lineend == -1):
                pywikibot.output(u"Line break not found after image " + image.title() + "not found in " + gallery.title())
              else:
                outputText = text[:linestart] + text[lineend + 1:]
                if not self.debug:
                  try:
                    # Save the page
                    self.put(gallery, outputText)
                  except pywikibot.LockedPage:
                    pywikibot.output(u"Page %s is locked; skipping." % outputPage.aslink())
                  except pywikibot.EditConflict:
                    pywikibot.output(u'Skipping %s because of edit conflict' % (outputPage.title()))
                  except pywikibot.SpamfilterError, error:
                    pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (outputPage.title(), error.url))
                if (text != outputText):
                  pywikibot.output(u"*** %s ***" % gallery.title())
                  pywikibot.showDiff(text, outputText)
      #There are many redirects left in the galleries
      except pywikibot.IsRedirectPage:
        pass
      except pywikibot.LockedPage:
        pywikibot.output(u"Page %s is locked; skipping." % outputPage.aslink())
      except pywikibot.EditConflict:
        pywikibot.output(u'Skipping %s because of edit conflict' % (outputPage.title()))
      except pywikibot.SpamfilterError, error:
        pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (outputPage.title(), error.url))
        
        
      
""" 
def removeScopeLinks(text):
  import re
  
  linkRE = re.compile('\[\[([^\|\]]*)\]\]')
  linkCaptionRE = re.compile('\[\[[^\|\]]*\|([^\|\]]*)\]\]')
  linkwRE = re.compile('{{w\|([^}]*)}}')
  
  return linkwRE.sub(r'\1', linkRE.sub(r'\1', linkCaptionRE.sub(r'\1', text)))

def makeSortScope(scope):
  import re
  
  italicRE = re.compile('\'\'([^\']*)\'\'')
  boldRE = re.compile('\'\'\'([^\']*)\'\'\'')
  return italicRE.sub(r'\1', boldRE.sub('\1', scope))
"""

def main():
  
  # Trigger debug mode
  debug = False
  for arg in pywikibot.handleArgs():
    if arg.startswith("-debug"):
      debug = True
  bot = EuseBot(debug)
  bot.run()

if __name__ == "__main__":
  try:
    main()
  finally:
    pywikibot.stopme()
