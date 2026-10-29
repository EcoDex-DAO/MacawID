const basePath = process.cwd();
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const { format, layerConfigurations, rarityDelimiter, shuffleLayerConfigurations, debugLogs, namePrefix, description, baseUri, uniqueDnaTorrance, extraMetadata, background, } = require(`${basePath}/src/config.js`);
const buildDir = `${basePath}/build`;
const layersDir = `${basePath}/layers`;

let metadataList = [];
let attributesList = [];
let dnaList = new Set();
const canvas = createCanvas(format.width, format.height);
const ctx = canvas.getContext("2d");

const buildSetup = () => {
  if (fs.existsSync(buildDir)) {
    fs.rmSync(buildDir, { recursive: true });
  }
  fs.mkdirSync(buildDir);
  fs.mkdirSync(`${buildDir}/json`);
  fs.mkdirSync(`${buildDir}/images`);
};

const getRarityWeight = (_str) => {
  let nameWithoutExtension = _str.slice(0, -4);
  let nameWithoutWeight = Number(nameWithoutExtension.split(rarityDelimiter).pop());
  return isNaN(nameWithoutWeight) ? 1 : nameWithoutWeight;
};

const cleanName = (_str) => {
  let nameWithoutExtension = _str.slice(0, -4);
  let nameWithoutWeight = nameWithoutExtension.split(rarityDelimiter).shift();
  return nameWithoutWeight;
};

const getElements = (path) => {
  return fs
    .readdirSync(path)
    .filter((item) => !/(^|\/)\.[^\/\.]/g.test(item))
    .map((i) => {
      return {
        id: i,
        name: cleanName(i),
        filename: i,
        path: `${path}/${i}`,
        weight: getRarityWeight(i),
      };
    });
};

const layersSetup = (layersOrder) => {
  return layersOrder.map((layerObj, index) => {
    return {
      id: index,
      elements: getElements(`${layersDir}/${layerObj.name}`),
      name: layerObj.name,
      blend: "source-over",
      opacity: 1,
    };
  });
};

const drawElement = async (layer, element) => {
  const image = await loadImage(`${element.path}`);
  ctx.drawImage(image, 0, 0, format.width, format.height);
  attributesList.push({
    trait_type: layer.name,
    value: element.name,
  });
};

const constructLayerToDna = (layers) => {
  let dna = "";
  layers.forEach((layer) => {
    const totalWeight = layer.elements.reduce((acc, element) => acc + element.weight, 0);
    let random = Math.floor(Math.random() * totalWeight);
    for (let i = 0; i < layer.elements.length; i++) {
      random -= layer.elements[i].weight;
      if (random < 0) {
        dna += `${layer.elements[i].id}`;
        break;
      }
    }
  });
  return dna;
};

const isDnaUnique = (_dna) => {
  return !dnaList.has(_dna);
};

const saveImage = (_editionCount) => {
  fs.writeFileSync(`${buildDir}/images/${_editionCount}.png`, canvas.toBuffer("image/png"));
};

const saveMetadata = (_editionCount) => {
  let metadata = {
    name: `${namePrefix} #${_editionCount}`,
    description: description,
    image: `${baseUri}/${_editionCount}.png`,
    edition: _editionCount,
    attributes: attributesList,
    ...extraMetadata,
  };
  metadataList.push(metadata);
  fs.writeFileSync(`${buildDir}/json/${_editionCount}.json`, JSON.stringify(metadata, null, 2));
};

const startCreating = async () => {
  let editionCount = 1;
  for (const layerConfig of layerConfigurations) {
    const layers = layersSetup(layerConfig.layersOrder);
    while (editionCount <= layerConfig.growEditionSizeTo) {
      let newDna = constructLayerToDna(layers);
      if (isDnaUnique(newDna)) {
        dnaList.add(newDna);
        ctx.clearRect(0, 0, format.width, format.height);
        attributesList = [];
        for (let i = 0; i < layers.length; i++) {
          await drawElement(layers[i], layers[i].elements[0]);
        }
        saveImage(editionCount);
        saveMetadata(editionCount);
        editionCount++;
      }
    }
  }
};

module.exports = { buildSetup, startCreating };
