const fs = require('fs');
try {
  let file = fs.readFileSync('lint.json', 'utf16le');
  if (!file.startsWith('[')) {
      file = fs.readFileSync('lint.json', 'utf8');
  }
  const data = JSON.parse(file);
  const msgs = [];
  data.forEach(d => {
    d.messages.forEach(m => {
       msgs.push(`${d.filePath}:${m.line} => ${m.ruleId}: ${m.message}`);
    })
  });
  console.log(msgs.join('\n'));
} catch (e) {
  console.error("Error parsing", e);
}
