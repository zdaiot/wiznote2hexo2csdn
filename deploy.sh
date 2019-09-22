
#!/bin/bash
echo -n "please enter git commit information:"
read  commit_information

git add .
git commit -m commit_information
git push origin master
