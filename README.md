

TS install

npm i -D typescript typed-struct @types/node  
npx tsc --init 
npx tsc index.ts
node index.js


npx tsc --project tsconfig.json; node index.js


building package
py -m build
py -m twine upload dist/*

py -m pip install --upgrade twine


run locally python .\src\main.py