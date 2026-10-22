// Read PNG bytes and report exact full-image sRGB/linear means. Never edits PNGs.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const original = path.join(__dirname, 'earth-detail-original.png');
const png = fs.readFileSync(original);
const chunks = [];
for (let i = 8; i < png.length;) {
  const length = png.readUInt32BE(i);
  if (png.toString('ascii', i + 4, i + 8) === 'IDAT') chunks.push(png.subarray(i + 8, i + 8 + length));
  i += length + 12;
}
const width = png.readUInt32BE(16), height = png.readUInt32BE(20);
if (png[24] !== 8 || ![2, 6].includes(png[25]) || png[28] !== 0) throw Error('Expected noninterlaced 8-bit RGB/RGBA PNG');
const channels = png[25] === 2 ? 3 : 4, stride = width * channels;
const filtered = zlib.inflateSync(Buffer.concat(chunks));
const pixels = Buffer.alloc(stride * height);
function paeth(a, b, c) {
  const p = a + b - c, da = Math.abs(p - a), db = Math.abs(p - b), dc = Math.abs(p - c);
  return da <= db && da <= dc ? a : db <= dc ? b : c;
}
for (let y = 0; y < height; y++) {
  const filter = filtered[y * (stride + 1)];
  for (let x = 0; x < stride; x++) {
    const i = y * stride + x;
    const left = x >= channels ? pixels[i - channels] : 0;
    const up = y ? pixels[i - stride] : 0;
    const diagonal = y && x >= channels ? pixels[i - stride - channels] : 0;
    const predictor = filter === 0 ? 0 : filter === 1 ? left : filter === 2 ? up : filter === 3 ? Math.floor((left + up) / 2) : filter === 4 ? paeth(left, up, diagonal) : NaN;
    if (!Number.isFinite(predictor)) throw Error('Unknown PNG filter');
    pixels[i] = (filtered[y * (stride + 1) + x + 1] + predictor) & 255;
  }
}
const linear = Array.from({length: 256}, (_, i) => {
  const c = i / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
});
const srgbMean = [0, 0, 0], linearMean = [0, 0, 0];
let linearLuminance = 0, srgbLuminance = 0;
for (let i = 0; i < pixels.length; i += channels) {
  for (let c = 0; c < 3; c++) { srgbMean[c] += pixels[i + c] / 255; linearMean[c] += linear[pixels[i + c]]; }
  linearLuminance += .2126 * linear[pixels[i]] + .7152 * linear[pixels[i + 1]] + .0722 * linear[pixels[i + 2]];
  srgbLuminance += (.2126 * pixels[i] + .7152 * pixels[i + 1] + .0722 * pixels[i + 2]) / 255;
}
const count = width * height;
for (let c = 0; c < 3; c++) { srgbMean[c] /= count; linearMean[c] /= count; }
linearLuminance /= count; srgbLuminance /= count;
let clampedRatioMean = 0, low = 0, high = 0;
for (let i = 0; i < pixels.length; i += channels) {
  const l = .2126 * linear[pixels[i]] + .7152 * linear[pixels[i + 1]] + .0722 * linear[pixels[i + 2]];
  const ratio = l / linearLuminance;
  clampedRatioMean += Math.max(.35, Math.min(2.25, ratio));
  if (ratio < .35) low++; if (ratio > 2.25) high++;
}
clampedRatioMean /= count;
const sha256 = crypto.createHash('sha256').update(png).digest('hex').toUpperCase();
if (sha256 !== '483D36A325CA6B05BBB8580DD3E238AF866F331D762976CB0064569FD7925F1B') throw Error('Original identity differs from reviewed image');
const report = {
  title: 'Ground albedo detail v12 — isolated staging candidate',
  stagingOnly: true, adopted: false,
  source: 'Built-in image_gen; original generated raster, no pixel edits',
  original: 'art/generated/ground-v12/earth-detail-original.png', sha256,
  prompt: 'art/generated/ground-v12/prompt.txt',
  width, height, bitDepth: 8, channels, sampleCount: count,
  colorAssumption: 'PNG RGB treated as sRGB, exact IEC sRGB inverse transfer per component; Rec.709 luminance',
  meanSRGBRGB: srgbMean, meanLinearRGB: linearMean,
  meanSRGBLuminance: srgbLuminance, meanLinearLuminance: linearLuminance,
  shaderRatioClamp: [.35, 2.25], clampedRatioMean,
  ratioLowClampFraction: low / count, ratioHighClampFraction: high / count,
  intendedTileMetres: 1.8, detailStrength: .55,
  resourceCopy: 'GameProject/Assets/BorrowedLight/Resources/Textures/GroundDetailV12.png',
  setupScript: 'tools/setup-ground-detail-v12.cs',
  shader: 'GameProject/Assets/BorrowedLight/Shaders/GroundDetail.shader',
  studyScript: 'GameProject/Assets/BorrowedLight/Runtime/GroundDetailStudy.cs',
  studyArgument: '-borrowedLightGroundDetailStudy',
  currentValidation: {originalHashVerified: true, sourceAnalysisOnly: true, unityCompilation: 'pending root', runtimeFixedPoseStudy: 'pending root', visualAcceptance: 'not established', performance: 'not measured'},
  detailFormula: '(1-strength)+strength*(clamp(linearLuminance/meanLinearLuminance,.35,2.25)/clampedRatioMean)',
  wholeImageMeanMultiplier: 1,
  baseMeadowUVAndColorUnchanged: true, originalMeadowNormalScale: .22,
  limitations: ['Mean multiplier is an exact authored-pixel mean; filtered/mipmapped projected frame mean is not guaranteed to equal one.', 'Texture repetition and GPU aliasing require actual fixed-camera runtime review.', 'No runtime compilation, visual acceptance, native/WebGL performance or release adoption established.']
};
fs.writeFileSync(path.join(__dirname, 'manifest.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
