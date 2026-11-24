set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src
printf '{"name":"cart","version":"1.2.0","type":"module","private":true,"scripts":{"test":"node --test"}}\n' > package.json
cat > src/cart.js <<'J'
export function subtotal(items) {
  let total = 0;
  for (let i = 1; i < items.length; i++) total += items[i].price * items[i].qty;
  return total;
}
J
printf "setup.sh\n" > .gitignore
git add -A && git commit -qm "1.2.0" && git tag v1.2.0
sed -i.bak 's/let i = 1/let i = 0/' src/cart.js && rm src/cart.js.bak
printf '{"name":"cart","version":"2.0.0","type":"module","private":true,"scripts":{"test":"node --test"}}\n' > package.json
git add -A && git commit -qm "fix: subtotal counts the first item (2.0.0)" && git tag v2.0.0
cat > SECURITY.md <<'J'
# Security policy

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |
J
printf '{"name":"cart","version":"2.1.0","type":"module","private":true,"scripts":{"test":"node --test"}}\n' > package.json
git add -A && git commit -qm "2.1.0" && git tag v2.1.0
