from resources.lib import parsedom

#link_html = "<a href='bla1.html' id='link1'>Link Test1</a><a href='bla2.html' id='link2'>Link Test2</a><a href='bla3.html' id='link3'>Link Test3</a>"

testFile = open('test.html')
link_html = testFile.read()
testFile.close()

ret1 = parsedom.parseDOM(link_html, "div", attrs = { "class": "box touchable" })
ret2 = parsedom.parseDOM(ret1, "h1")
#ret3 = parsedom.parseDOM(ret2, "a", None , ret = "href")
#print repr(ret1) # Prints ['bla1.html']
#print repr(ret2) # Prints ['Link Test2']
print repr(ret2) # Prints ['link3']