import sharp from "sharp";
import { db } from "./db.js";

// Stores the original and a 512px thumbnail, then records the photo.
export async function handleUpload(file) {
  const thumb = await sharp(file.buffer).resize(512).jpeg().toBuffer();
  const id = db.prepare("INSERT INTO photos (name, size) VALUES (?, ?)").run(file.originalname, file.size).lastInsertRowid;
  await saveBlob(`originals/${id}`, file.buffer);
  await saveBlob(`thumbs/${id}.jpg`, thumb);
  return id;
}

async function saveBlob(path, buffer) {
  const { writeFile } = await import("node:fs/promises");
  await writeFile(`storage/${path}`, buffer);
}
