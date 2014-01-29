
def templateparameter( text ) :

  last = ''
  newtext = ''
  curl = 0
  squr = 0

  for c in text:
    if c == '|' and curl == 0 and squr == 0 :
      break

    if c == '[' and last == '[' :
      squr += 1
      last = ''
    if c == ']' and last == ']' :
      squr -= 1
      last = ''
    if c == '{' and last == '{' :
      curl += 1
      last = ''
    if c == '}' and last == '}' :
      curl -= 1
      last = ''

    if curl < 0 or squr < 0 :
      break

    newtext += c
    last = c

  return newtext


print templateparameter( "Hallo [[user:hallo|welt]] in {{w|biler}}}" )
