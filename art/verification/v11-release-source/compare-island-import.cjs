// Compare Unity-imported assets, independently of the Blender author's manifest.
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const { isDeepStrictEqual: equal } = require('node:util');
const [basePath, candidatePath, allowedCsv] = process.argv.slice(2);
assert(basePath && candidatePath && allowedCsv, 'Supply baseline JSON, candidate JSON and comma-separated allowed mesh names.');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const base = read(basePath), candidate = read(candidatePath), allowed = new Set(allowedCsv.split(','));
const sort = xs => [...xs].sort((a, b) => a.name.localeCompare(b.name));
const oldMeshes = new Map(base.meshes.map(x => [x.name, x]));
const meshNamesMatch = equal([...oldMeshes.keys()].sort(), candidate.meshes.map(x => x.name).sort());
const checks = candidate.meshes.map(mesh => {
    const old = oldMeshes.get(mesh.name);
    return { name: mesh.name, allowedChange: allowed.has(mesh.name),
        unchanged: !!old && equal(old, mesh), transformUnchanged: !!old && equal(old.matrix, mesh.matrix),
        trianglesBefore: old?.triangles, trianglesAfter: mesh.triangles,
        geometryChanged: !!old && old.geometrySHA256 !== mesh.geometrySHA256,
        materialsChanged: !!old && !equal(old.materials, mesh.materials),
        normalsComplete: mesh.normalCount === mesh.vertices, colorsComplete: mesh.colorCount === mesh.vertices };
});
const report = {
    scope: 'Unity importer comparison: non-target mesh arrays/materials/transforms and all anchors must remain identical. Target shape quality still requires visual review.',
    baseline: path.resolve(basePath), candidate: path.resolve(candidatePath),
    trianglesBefore: base.totalTriangles, trianglesAfter: candidate.totalTriangles,
    meshNamesMatch, anchorsUnchanged: equal(sort(base.anchors), sort(candidate.anchors)),
    nonTargetUnchanged: checks.filter(x => !x.allowedChange).every(x => x.unchanged),
    allTransformsUnchanged: checks.every(x => x.transformUnchanged),
    vertexChannelsComplete: checks.every(x => x.normalsComplete && x.colorsComplete),
    targetChangesPresent: checks.some(x => x.allowedChange && x.geometryChanged),
    allAllowedNamesExist: [...allowed].every(name => oldMeshes.has(name)),
    triangleBudgetPassed: candidate.totalTriangles <= 550000,
    checks
};
report.passed = report.meshNamesMatch && report.anchorsUnchanged && report.nonTargetUnchanged && report.allTransformsUnchanged && report.vertexChannelsComplete && report.targetChangesPresent && report.allAllowedNamesExist && report.triangleBudgetPassed;
fs.writeFileSync(path.join(path.dirname(candidatePath), 'unity-import-comparison.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ passed: report.passed, trianglesBefore: report.trianglesBefore, trianglesAfter: report.trianglesAfter,
    changed: checks.filter(x => !x.unchanged).map(x => x.name), failedProtected: checks.filter(x => !x.allowedChange && !x.unchanged).map(x => x.name),
    anchorsUnchanged: report.anchorsUnchanged, vertexChannelsComplete: report.vertexChannelsComplete }));
if (!report.passed) process.exitCode = 1;
