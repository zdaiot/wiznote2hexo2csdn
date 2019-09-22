
#!/bin/bash
echo -n "please enter git commit information:"
read commitInformation
git add .
git commit -m commitInformation
git push origin master
