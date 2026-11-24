set -eu
git init -q -b main
git config user.name "Repo Owner"; git config user.email owner@example.com
mkdir -p src public
printf '{"name":"static-serve","version":"1.0.0","type":"module"}\n' > package.json
cat > src/serve.js <<'J'
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const server = createServer(async (req, res) => {
  try {
    res.end(await readFile(join("public", decodeURIComponent(req.url))));
  } catch {
    res.statusCode = 404;
    res.end();
  }
});
J
printf "hello\n" > public/index.html
printf "setup.sh\n" > .gitignore
git add -A && git commit -qm "static server"
