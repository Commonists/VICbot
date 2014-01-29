#!/usr/bin/python

import sys, os
print os.environ['HOME']
sys.path.append(os.environ['HOME'] + '/core')

import pywikibot
import MySQLdb
import re
import math
import string
import unicodedata
#import htmlentitydefs
import urllib
import viutil

from urllib import FancyURLopener
#from PHPUnserialize import *
    
class VICbot:

  def __init__(self, debug):
    """
    Constructor. Parameters:
      * debug     - If True, doesn't do any real changes, but only shows
                    what would have been changed.
    """
    self.debug = debug
    self.site = pywikibot.getSite()

  # Give up if replag on main server is too high
  def put(self, page, text):
    page.put(text)
    
  def scrubscope(self, t) :
    link2RE = re.compile('\[\[(?:[^\|\]]+\|){0,1}([^\|\]]+)\]\]') 
    link3RE = re.compile('\{\{w\|([^\|\}]+)\}\}')
    t2 = link2RE.sub( r'\1', t )
    t3 = link3RE.sub( r'\1', t2 )
    return t3

  def run(self):
  
    timeRE = re.compile('(\d\d):(\d\d), (\d\d?) (January|February|March|April|May|June|July|August|September|October|November|December) (\d\d\d\d) \((UTC|GMT)\)')
    userRE = re.compile('\[\[([Uu]ser|[Bb]enutzer|[Gg]ebruiker):([^\|\]]+)[^\]]*\]\]')
    linkRE = re.compile('\[\[([^\|\]:]+)[^\]]*\]\]')
    emptyRE = re.compile('^===[^=]+===\s+^{\{VICs\s+^\}\}\s*', re.MULTILINE)
    #galleryRE = re.compile('^\s*[Ii]mage:([^\|]+)')
    galleryRE = re.compile('^\s*([Ii]mage|[Ff]ile):([^\|]+)')
    viscopeRE = re.compile('^\{\{[vV]I\|(.+)\|[^\|]+\|')
    scopelistRE = re.compile('\*\s*\[\[:[Ii]mage:([^\|\]]+).*\|(.+)\]\]\s*$')

    userNote = {}
    removeCandidates = []
    tagImages = []
    scopeList = []
    numChanges = 0

    pageName = 'Commons:Valued_image_candidates'
    
    #
    # prepare a random sample for COM:VI
    #

    pywikibot.setAction( "preparing a new random sample of four valued images" )

    try:
      connection = MySQLdb.connect(host="commonswiki.labsdb", db="commonswiki_p", read_default_file="~/replica.my.cnf" )
      cursor = connection.cursor() 
      cursor.execute( "select page_title from templatelinks, page where tl_title='VI' and tl_namespace=10 and page_namespace=6 and page_id=tl_from order by RAND() limit 4" )
    except MySQLdb.OperationalError, message: 
      errorMessage = "Error %d:\n%s" % (message[ 0 ], message[ 1 ] ) 
    else:
      data = cursor.fetchall()
      cursor.close()
      connection.close()

      sample = u"<gallery>\n"

      for row in range(len(data)):
        name = data[row][0].decode('utf-8')
        scope = ''

        page = pywikibot.Page(self.site, 'File:%s' % name )
        text = ""
        if page.exists() :
          text = page.get(get_redirect=True)

          for line in string.split(text, "\n") :
 
            # find first scope
            scopematch = viscopeRE.search( line ) 
            if scopematch != None :
              scope = scopematch.group(1)
              continue

        else :
          print "Odd, VI image page (%s) does not exist!" % name.encode("utf-8")
          continue

        sample += u"File:%s|%s\n" % ( name, scope )

      sample += u"</gallery>"
      print "%s" % sample.encode("utf-8")

      page = pywikibot.Page(self.site, 'Commons:Valued_images/sample' )
      if not self.debug:
        page.put( sample )
      else:
        oldtext = page.get(get_redirect=True)
        pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
        pywikibot.showDiff(oldtext, sample)

    #sys.exit(0);

    #
    # now fetch potential candidate pages
    #
    
    try:
      connection = MySQLdb.connect(host="commonswiki.labsdb", db="commonswiki_p", read_default_file="~/replica.my.cnf" )
      cursor = connection.cursor() 
      #cursor.execute( "select /* SLOW OK */ page_title, GROUP_CONCAT( DISTINCT cl_to SEPARATOR '|') from revision, page left join categorylinks on page_id = cl_from  where page_latest=rev_id and page_title like 'Valued_image_candidates/%' and page_namespace=4 and ( TO_DAYS(rev_timestamp) - TO_DAYS(CURRENT_DATE) ) > -5 group by page_id" )
      cursor.execute( "select /* SLOW_OK */ page_title, GROUP_CONCAT( DISTINCT cl_to SEPARATOR '|') from revision, page left join categorylinks on page_id = cl_from  where page_latest=rev_id and page_title like 'Valued_image_candidates/%' and page_namespace=4 and ( TO_DAYS(CURRENT_DATE) - TO_DAYS(rev_timestamp) ) < 25 group by page_id" )
    except MySQLdb.OperationalError, message: 
      errorMessage = "Error %d:\n%s" % (message[ 0 ], message[ 1 ] ) 
      print "--- MySQL Error ---"
      print errorMessage
    else:
      data = cursor.fetchall() 
      cursor.close()
      connection.close()
      
    candpages = [ "/candidate_list", "/Most valued review candidate list" ]

    candidates = ''
    for candpage in candpages :
      page = pywikibot.Page(self.site, pageName + candpage )
      text = viutil.unescape( page.get(get_redirect=True) )

      # abort if the qicbot marker is missing from the page 
      if string.find( text, "<!-- VICBOT_ON -->") < 0 :
        print "the string <!-- VICBOT_ON --> was not found on page " + pageName + candpage
      else :
        candidates += text



    #
    # get potential candidates from db
    #
    
    for row in range(len(data)):
      name = data[row][0]
      print name
      try:
      	cats = data[row][1]
      except IndexError:
	cats = None

      if cats == None :
        #print "Candidate %s has no categories!" % name.encode("utf-8")
        continue

      catlist = cats.split('|')

      status = 0

      for cat in catlist :
        if cat == 'Supported_valued_image_candidates' :
          status = 0
        if cat == 'Opposed_valued_image_candidates' :
          status = 0
        if cat == 'Promoted_valued_image_candidates' :
          status = 1
        if cat == 'Undecided_valued_image_candidates' :
          status = -1
        if cat == 'Declined_valued_image_candidates' :
          status = -1
        if cat == 'Discussed_valued_image_candidates' :
          status = 0
        if cat == 'Nominated_valued_image_candidates' :
          status = 0

      if status == 0 :
        print ("Nothing to do here (%s, %s)" % ( name.decode('utf-8'), cats )).encode("utf-8")
        continue

      #
      # get nomination subpage
      #
    
      page = pywikibot.Page(self.site, 'Commons:' + name.decode('utf-8') )
      text = ""
      if page.exists() :
        text = page.get(get_redirect=True)
      else :
        print "Odd, VIC subpage does not exist!"
        continue

      #
      # extract parameters
      #
    
      subpage = ''
      image   = ''
      scope   = ''
      nominator = ''
      review = ''
      recordingReview = False
    
      for rawline in string.split(text, "\n") :
        line = rawline.lstrip(' ')

        if line[:9] == '|subpage=' and subpage == '' :
          subpage = viutil.unescape( line[9:] ).lstrip(' ')
        if line[:7] == '|image=' and image == '' :
          image = line[7:]
        if line[:7] == '|scope=' and scope == '' :
          scope = line[7:]
        if line[:11] == '|nominator=' and nominator == '' :
          user = userRE.search(line)
          if user != None :
            nominator = user.group(2)

        if line[:8] == '|review=' :
          recordingReview = True
        if recordingReview :
          review += rawline + "\n"

      if image == '' or scope == '' or nominator == '' :
        if image == '' :
          print "image missing"
        if scope == '' :
          print "scope missing"
        if nominator == '' :
          print "nominator missing"
        print "Candidate %s is missing cruicial parameters" % name.decode('utf-8').encode("utf-8")
        continue
  
      if subpage == '' :
        subpage = image

      if string.find( candidates.replace( ' ', '_' ), subpage.replace( ' ', '_' ) ) < 0 :
        print "Candidate %s is not listed, I assume it was already handled!" % subpage.encode("utf-8")
        continue

      if string.find( review, '}}' ) < 0 :
        print "Unable to extract the review"
        review = '}}'

      print ("Handling (%d) %s on %s, nominated by %s" % ( status, image, subpage, nominator )).encode("utf-8")
      numChanges += 1

      # queue for removal from candidate list
      removeCandidates.append(subpage)

      if status == 1:

        #spParam = ''
        #if subpage != image :
        spParam = '|subpage=' + subpage
    
        # queue user notification
        try:
          userNote[nominator] += "{{VICpromoted|%s|%s%s%s\n" % ( image, scope, spParam, review )
        except KeyError:
          userNote[nominator] = "{{VICpromoted|%s|%s%s%s\n" % ( image, scope, spParam, review ) 

        # queue image page tagging
        tagImages.append( [ image, "{{subst:VI-add|%s%s}}\n" % ( scope, spParam ), u"File:%s|%s" % (image, scope)] )

        # queue for insertion into alphabetical scope list
        scopeList.append( [ image, scope ] )


    # no writing, just debugging
    #for item in tagImages :
    #	print ("Tag %s with %s" % ( item[0], item[1]) ).encode("utf-8")
    #for key in userNote.keys() :
    #	print userNote[key]
        
    #sys.exit(0)
    
    #
    # Alphabetical scope list (this is alway executed as the list might have been edited manually)
    #
    
    page = pywikibot.Page(self.site, 'Commons:Valued_images_by_scope' )
    pywikibot.setAction("Insert into and resort alphabetical VI list by scope")
    if page.exists() :
      text = page.get(get_redirect=True)
      oldtext = text
      newList = {}

      for entry in scopeList :
        scrubbed = self.scrubscope(entry[1])
        newList[ scrubbed.replace("'","").upper() ] = "*[[:File:%s|%s]]" % ( entry[0], scrubbed ) 

      for line in string.split(text, "\n") :
        match = scopelistRE.search(line)
        if match != None :
          newList[ match.group(2).replace("'","").upper() ] = line

      keys = newList.keys()
      keys.sort()
      sortedList = "\n".join( map( newList.get, keys) )

      listPrinted = False
      newText = ''
      for line in string.split(text, "\n") :
        match = scopelistRE.search(line)
        if match == None :
          newText += line + "\n"
        elif not listPrinted :
          listPrinted = True
          newText += sortedList + "\n"

      if not self.debug:
        page.put( newText.rstrip("\n") )
      else:
        pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
        pywikibot.showDiff(oldtext, newText.rstrip("\n"))

    if numChanges == 0 :
      print "No action taken"
      sys.exit(0)

    #
    # removing candidates from candidate lists
    #
    
    pywikibot.setAction( "extract processed nominations" )
    candidates = ''
    for candpage in candpages :
      newText = ''
      page = pywikibot.Page(self.site, pageName + candpage )
      candidates = page.get(get_redirect=True)
      oldtext = candidates
      for line in string.split(candidates, "\n") :
        keepLine = True
        uline = viutil.unescape( line )

        for remove in removeCandidates :
          #if string.find( uline.replace( ' ', '_' )  , remove.replace( ' ', '_' )  ) >= 0:
          if uline.lstrip("| ").replace( ' ', '_' ) == remove.replace( ' ', '_' ) :
            keepLine = False
            print "remove %s" % line.encode("utf-8")
            print "  matched %s and %s" % ( uline.replace( ' ', '_' ).encode("utf-8") , remove.replace( ' ', '_' ).encode("utf-8") )
            continue
  
        if keepLine :
          newText += line + "\n"

      #print newText.encode("utf-8")
      if not self.debug:
        page.put( emptyRE.sub( '', newText ).rstrip("\n") )
      else:
        pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
        pywikibot.showDiff(oldtext, emptyRE.sub( '', newText ).rstrip("\n"))

    #
    # Tag images
    #
    
    pywikibot.setAction("Tag promoted Valued Image")
    for image in tagImages :
      page = pywikibot.Page(self.site, 'File:' + image[0] )

      if page.exists() :
        #TODO already tagged maybe?
        text = page.get(get_redirect=True)
        oldtext = text
        text += "\n" + image[1]
        if not self.debug:
          page.put(text)
        else:
          pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
          pywikibot.showDiff(oldtext, text)
      else :
        print "Oops " + image[0].encode("utf-8") + " doesn't exist..."

    #    
    # Removed sorted images from Valued images/Recently promoted and dispatch them in galleries
    #
    
    self.dispatchRecentlyPromoted()

    #    
    # Add newly promoted images in Valued images/Recently promoted
    #
    
    self.populateRecentlyPromoted(tagImages)
    
    #
    # User notifications
    #
    
    pywikibot.setAction("Notify user of promoted Valued Image(s)")
    for key in userNote.keys() :
      page = pywikibot.Page(self.site, "User talk:" + key )

      if page.exists() :
        text = page.get(get_redirect=True)
        oldtext = text
      else :
        oldtext = ''
        text = 'Welcome to commons ' + key + ". What better way than starting off with a Valued Image promotion could there be? :-) --~~~~\n\n"
  
      text = text + "\n==Valued Image Promotion==\n" + userNote[key]
      if not self.debug:
        page.put(text)
      else:
        pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
        pywikibot.showDiff(oldtext, text)

    #
    # Tag images in scope galleries
    #
    
    pywikibot.setAction("Tag images in galleries")
    for entry in scopeList :
      tinySuccess = False

      # is there a link in the scope line?
      link = linkRE.search( entry[1] ) 
      if link != None :
        page = pywikibot.Page(self.site, link.group(1) )
      else :
        page = pywikibot.Page(self.site, entry[1] )

      if page.exists() :
        try :
          text = page.get(get_redirect=True)
          newText = ''
          for line in text.split("\n") :
            gallery = galleryRE.search( line )
            if gallery != None :
              if gallery.group(2).replace( ' ', '_' ) == entry[0].replace( ' ', '_' ) :
                newText += "%s|{{VI-tiny}} %s\n" % ( line.split('|')[0], "|".join( line.split('|')[1:] ) )
                tinySuccess = True
                print "success! " + entry[1].encode("utf-8")
              else :
                newText += line + "\n"
            else :
              newText += line + "\n"
          if not self.debug:
            page.put( newText.rstrip("\n") )
            #print newText.encode("utf-8")
          else:
            pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
            pywikibot.showDiff(text, newText.rstrip("\n"))
        except :
          print "exception in gallery tagging"
      else :
        print "Gallery %s does not exist" % entry[1].encode("utf-8")

      if not tinySuccess :
        page = pywikibot.Page(self.site, pageName + "/tag_galleries" )
        if page.exists() :
          text = page.get(get_redirect=True)
          oldtext = text
        else :
          oldtext = ''
          text = "add <nowiki>{{VI-tiny}}</nowiki> at the gallery that matches the scope best and then remove the entry from this list\n\n"

        text = text + "\n*[[:File:%s|%s]]" % ( entry[0], self.scrubscope(entry[1]) )
        if not self.debug:
          page.put(text)
          #print text.encode("utf-8")
        else:
          pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % page.title())
          pywikibot.showDiff(oldtext, text)

    # done!

  def dispatchRecentlyPromoted(self):
    """
      Takes sorted images from [[Commons:Valued images/Recently promoted]] and places them in [[Commons:Valued images by topic]]
      
      Arguments :
    """
    
    # Set the edit summary message
    pywikibot.setAction(u'Adding recently categorized [[COM:VI|valued images]] to the [[:Category:Galleries of valued images|VI galleries]]')
    pywikibot.output(u'Adding recently categorized VIs to the VI galleries')
    
    recentPage = pywikibot.Page(self.site, u'Commons:Valued images/Recently promoted')
    galleryPrefix = u'Commons:Valued images by topic/'
    
    recentOldText = ""
    recentNewText = ""
    
    try:
      recentOldText = recentPage.get(get_redirect=True)
    except pywikibot.NoPage:
      pywikibot.output(u"Page %s does not exist; skipping." % recentPage.aslink())
      return
    except pywikibot.IsRedirectPage:
      pywikibot.output(u"Page %s is a redirect; skipping." % recentPage.aslink())
    
    #The structure recording the needed moves
    moveMap = {}
    
    #Find beginning of the gallery
    inGallery = False
    for line in recentOldText.split('\n'):
      if not inGallery:
        if line == u'<gallery>':
          inGallery=True
          recentNewText += line + '\n'
          continue
        else:
          recentNewText += line + '\n'
      else:
        if line == u'</gallery>':
          inGallery=False
          recentNewText += line + '\n'
          continue
        else:
          #Here we process an image
          firstPipePosition = line.find(u'|')
          fileName = line[0:firstPipePosition]
          caption = line[firstPipePosition + 1:]
          if caption.startswith(u'{{VICbotMove|'):
            #The VI is categorized already
            firstPipe = caption.find(u'|')
            lastPipe = caption.rfind(u'|')
            endOfTemplate = caption.rfind(u'}}')
            scope = caption[firstPipe+1:lastPipe]
            subpage = caption[lastPipe+1:endOfTemplate]
            if subpage not in moveMap.keys():
              moveMap[subpage] = []
            moveMap[subpage].append((fileName, scope))
          else:
            #The VI is not categorized
            recentNewText += line + '\n'
    
    #Add pictures in galleries
    for subpage in moveMap.keys():
      galleryPage = pywikibot.Page(self.site, galleryPrefix + subpage)
      try:
        currentGalleryText = galleryPage.get(get_redirect=True)
      except pywikibot.NoPage:
        pywikibot.output(u'****************************************************')
        pywikibot.output(u"Page %s does not exist; skipping." % galleryPage.aslink())
        pywikibot.output(u"Skipped lines:")
        for pair in moveMap[subpage]:
          pywikibot.output(pair[0] + u'|' + pair[1])
        pywikibot.output(u'****************************************************')
        continue
      except pywikibot.IsRedirectPage:
        pywikibot.output(u'****************************************************')
        pywikibot.output(u"Page %s is a redirect; skipping." % galleryPage.aslink())
        pywikibot.output(u"Skipped lines:")
        for pair in moveMap[subpage]:
          pywikibot.output(pair[0] + u'|' + pair[1])
        pywikibot.output(u'****************************************************')
        continue
      endOfGal = currentGalleryText.rfind(u'\n</gallery>')
      if endOfGal < 0:
        pywikibot.output(u'****************************************************')
        pywikibot.output(u"Gallery on page %s is malformed; skipping." % galleryPage.aslink())
        pywikibot.output(u"Skipped lines:")
        for pair in moveMap[subpage]:
          pywikibot.output(pair[0] + u'|' + pair[1])
        pywikibot.output(u'****************************************************')
        continue
      newGalleryText = currentGalleryText[:endOfGal]
      for pair in moveMap[subpage]:
        newGalleryText += u'\n' + pair[0] + u'|' + pair[1]
      newGalleryText += currentGalleryText[endOfGal:]
      if not self.debug:
        try:
          self.put(galleryPage, newGalleryText)
        except pywikibot.LockedPage:
          pywikibot.output(u"Page %s is locked; skipping." % galleryPage.aslink())
        except pywikibot.EditConflict:
          pywikibot.output(u'Skipping %s because of edit conflict' % (galleryPage.title()))
        except pywikibot.SpamfilterError, error:
          pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (galleryPage.title(), error.url))
      pywikibot.output(u"*** %s ***" % galleryPage.title())
      pywikibot.showDiff(currentGalleryText, newGalleryText)
    
    #update the "Recently promoted" page
    recentNewText = recentNewText.rstrip()
    if not self.debug:
      try:
        self.put(recentPage, recentNewText)
        pass
      except pywikibot.LockedPage:
        pywikibot.output(u"Page %s is locked; skipping." % recentPage.aslink())
      except pywikibot.EditConflict:
        pywikibot.output(u'Skipping %s because of edit conflict' % (recentPage.title()))
      except pywikibot.SpamfilterError, error:
        pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (recentPage.title(), error.url))
    if (recentNewText != recentOldText):
      pywikibot.output(u"*** %s\03{default} ***" % recentPage.title())
      pywikibot.showDiff(recentOldText, recentNewText)

  def populateRecentlyPromoted(self, tagImages):
    """
      Adds the newly promoted VIs in [[Commons:Valued images/Recently promoted]]
      
      Arguments :
      tagImages   list constructed in the main program
    """
    pywikibot.setAction(u'Preparing newly promoted [[COM:VI|Valued Images]] for sorting')
    recentPage = pywikibot.Page(self.site, "Commons:Valued images/Recently promoted")
      
    try:
      currentOutputText = recentPage.get(get_redirect=True)
    except pywikibot.NoPage:
      pywikibot.output(u"Page %s does not exist; skipping." % page.aslink())
      return
    except pywikibot.IsRedirectPage:
      pywikibot.output(u"Page %s is a redirect; skipping." % page.aslink())
      return
    except:
      pywikibot.output(page.aslink())
      print "An unhandled exception occured, here's the traceback!"
      traceback.print_exc()
      return
    
    endOfGal = currentOutputText.rfind(u'\n</gallery>')
    if endOfGal < 0:
      pywikibot.output(u"Gallery on page %s is malformed; skipping." % outputPage.aslink())
    else:
      newOutputText = currentOutputText[:endOfGal]
      for image in tagImages:
        newOutputText += u"\n" + image[2]
      newOutputText += currentOutputText[endOfGal:]
        
    if not self.debug:
      try:
        self.put(recentPage, newOutputText)
      except pywikibot.LockedPage:
        pywikibot.output(u"Page %s is locked; skipping." % outputPage.aslink())
      except pywikibot.EditConflict:
        pywikibot.output(u'Skipping %s because of edit conflict' % (outputPage.title()))
      except pywikibot.SpamfilterError, error:
        pywikibot.output(u'Cannot change %s because of spam blacklist entry %s' % (outputPage.title(), error.url))
    else:
      if (currentOutputText != newOutputText):
        pywikibot.output(u">>> \03{lightpurple}%s\03{default} <<<" % recentPage.title())
        pywikibot.showDiff(currentOutputText, newOutputText)
    return

def main():
  
  # Trigger debug mode
  debug = False
  for arg in pywikibot.handleArgs():
    if arg.startswith("-debug"):
      debug = True
  bot = VICbot(debug)
  bot.run()

if __name__ == "__main__":
  try:
    main()
  finally:
    pywikibot.stopme()
