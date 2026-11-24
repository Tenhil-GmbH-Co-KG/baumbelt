#!/usr/bin/env bash

GREEN="\033[0;32m"
NC="\033[0m" #No color

echo_green() {
  echo -e $GREEN$1$NC
}

help_function() {
  # Display help text
  echo "Deploy script for Baumbelt"
  echo "Usage: $0 [--dry-run|--help|-h]"
  echo "Options:"
  echo -e "\t--dry-run\tDry run: Does not create "
  echo -e "\t--help,-h\tDisplay this help text"
  exit 1
}

run() {
  if [ "$dry_run" == true ] ; then
    echo "[dry run]" $1
  else
    $1
  fi
}

while [[ $# -gt 0 ]]; do
   case "${1}" in
      -h|--help) # display help
         help_function
         exit;;
      --dry-run)
         dry_run=true
         shift;;
     *) # Invalid option
         echo "Error: Invalid option ${1}"
         exit;;
   esac
done

script_dirname=$(dirname "$0")

echo_green "Checkout develop..."
run "git checkout develop"
echo_green "Pull develop..."
run "git pull origin develop"

if [ "$dry_run" == true ] ; then
  echo_green "Bump Version (dry run)..."
  python "$script_dirname/bump-version.py" --dry-run
else
  echo_green "Bump Version..."
  python "$script_dirname/bump-version.py"
fi

pyproject_toml="$script_dirname/../pyproject.toml"
new_version=$(grep -oP "(?<=version = \").*(?=\")" $pyproject_toml)

if [ "$dry_run" == true ] ; then
  echo_green "[dry run] Version has not changed and is still: $new_version"
else
  echo_green "New version number: $new_version"
fi

echo_green "Push version changes to develop..."
run "git push origin develop"
echo_green "checkout main..."
run "git checkout main"
echo_green "Merge develop into main..."
run "git merge develop"
echo_green "Push changes to main..."
run "git push origin main"
echo_green "push tag with new version number..."
run "git push origin tag '$new_version'"
