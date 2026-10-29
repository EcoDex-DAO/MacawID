const basePath = process.cwd();
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const { format, baseUri, description, background, uniqueDnaTorrance, layerConfigurations, rarityDelimiter, preview, shuffleLayerConfigurations, debugLogs, extraMetadata, namePrefix, network, solanaMetadata } = require(`${basePath}/src/config.js`);
const { NETWORK } = require(`${basePath}/constants/network.js`);

let metadataList = [];
let attributesList = [];

const buildSetup = () => {
  if (fs.existsSync(`${basePath}/build`)) {
    fs.rmSync(`${basePath}/build`, { recursive: true });
  }
  fs.mkdirSync(`${basePath}/build`);
  fs.mkdirSync(`${basePath}/build/json`);
  fs.mkdirSync(`${basePath}/build/images`);
};

const getElements = (path) => {
  return fs
    .readdirSync(path)
    .filter((item) => item.endsWith(".png"))
    .map((item, index) => {
      const name = item.split(rarityDelimiter).shift();
      const weight = Number(item.split(rarityDelimiter).pop().replace(".png", ""));
      return {
        id: index,
        name: name,
        filename: item,
        path: `${path}/${item}`,
        weight: weight,
      };
    });
};

const layersSetup = (layersOrder) => {
  return layersOrder.map((layerObj, index) => ({
    id: index,
    name: layerObj.name,
    elements: getElements(`${basePath}/layers/${layerObj.name}`),
  }));
};

const drawElement = async (ctx, layer, element) => {
  const image = await loadImage(element.path);
  ctx.drawImage(image, 0, 0, format.width, format.height);
};

const startCreating = async () => {
  const canvas = createCanvas(format.width, format.height);
  const ctx = canvas.getContext("2d");

  const layers = layersSetup(layerConfigurations[0].layersOrder);

  for (let i = 1; i <= layerConfigurations[0].growEditionSizeTo; i++) {
    ctx.clearRect(0, 0, format.width, format.height);

    if (background.generate) {
      ctx.fillStyle = background.default;
      ctx.fillRect(0, 0, format.width, format.height);
    }

    let attributes = [];
    for (const layer of layers) {
      const rand = Math.random() * layer.elements.reduce((a, b) => a + b.weight, 0);
      let sum = 0;
      let selected;
      for (const el of layer.elements) {
        sum += el.weight;
        if (rand < sum) {
          selected = el;
          break;
        }
      }

      await drawElement(ctx, layer, selected);

      attributes.push({
        trait_type: layer.name,
        value: selected.name,
      });
    }

    const buffer = canvas.toBuffer("image/png");
    fs.writeFileSync(`${basePath}/build/images/${i}.png`, buffer);

    let tempMetadata = {
      name: `${namePrefix} #${i}`,
      description: description,
      image: `${baseUri}/${i}.png`,
      edition: i,
      attributes: attributes,
    };

    if (network === NETWORK.sol) {
      tempMetadata = {
        name: `${namePrefix} #${i}`,
        symbol: solanaMetadata.symbol,
        description: description,
        seller_fee_basis_points: solanaMetadata.seller_fee_basis_points,
        image: `${i}.png`,
        external_url: solanaMetadata.external_url,
        edition: i,
        collection: solanaMetadata.collection,
        ...extraMetadata,
        attributes: attributes,
        properties: {
          files: [
            {
              uri: `${i}.png`,
              type: "image/png",
            },
          ],
          category: "image",
          creators: solanaMetadata.creators,
        },
      };
    }

    metadataList.push(tempMetadata);
    fs.writeFileSync(`${basePath}/build/json/${i}.json`, JSON.stringify(tempMetadata, null, 2));
  }
};

module.exports = { startCreating, buildSetup };

