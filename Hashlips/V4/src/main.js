const basePath = process.cwd();
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const { format, baseUri, description, background, uniqueDnaTorrance, layerConfigurations, rarityDelimiter, extraMetadata, namePrefix, network, solanaMetadata } = require(`${basePath}/src/config.js`);
const { NETWORK } = require(`${basePath}/constants/network.js`);

let metadataList = [];

const canvas = createCanvas(format.width, format.height);
const ctx = canvas.getContext("2d");

const buildSetup = () => {
  if (fs.existsSync(`${basePath}/build`)) {
    fs.rmSync(`${basePath}/build`, { recursive: true });
  }
  fs.mkdirSync(`${basePath}/build`);
  fs.mkdirSync(`${basePath}/build/json`);
  fs.mkdirSync(`${basePath}/build/images`);
};

const saveImage = (_editionCount) => {
  fs.writeFileSync(`${basePath}/build/images/${_editionCount}.png`, canvas.toBuffer("image/png"));
};

const generateMetadata = (edition, attributes) => {
  const tempMetadata = {
    name: `${namePrefix} #${String(edition).padStart(4, "0")}`,
    symbol: solanaMetadata.symbol,
    description: description,
    seller_fee_basis_points: solanaMetadata.seller_fee_basis_points,
    image: `${edition}.png`,
    external_url: `https://www.quipecos.com/nft/lgm/${edition}`,
    edition: edition,
    collection: solanaMetadata.collection,
    ...extraMetadata,
    attributes: attributes,
    properties: {
      files: [{ uri: `${edition}.png`, type: "image/png" }],
      category: "image",
      creators: solanaMetadata.creators,
    },
  };
  metadataList.push(tempMetadata);
  fs.writeFileSync(`${basePath}/build/json/${edition}.json`, JSON.stringify(tempMetadata, null, 2));
};

const drawBackground = () => {
  ctx.fillStyle = background.default;
  ctx.fillRect(0, 0, format.width, format.height);
};

const drawElement = async (element) => {
  const image = await loadImage(`${element.path}`);
  ctx.drawImage(image, 0, 0, format.width, format.height);
};

const startCreating = async () => {
  let editionCount = 0;

  for (let i = 0; i < layerConfigurations[0].growEditionSizeTo; i++) {
    drawBackground();

    const attributes = [];

    for (const layer of layerConfigurations[0].layersOrder) {
      const layerDir = `${basePath}/layers/${layer.name}`;
      const files = fs.readdirSync(layerDir).filter((f) => f.endsWith(".png"));

      const element = files[Math.floor(Math.random() * files.length)];
      const elementPath = `${layerDir}/${element}`;
      const traitValue = element.split(rarityDelimiter)[0].replace(".png", "");

      attributes.push({ trait_type: layer.name, value: traitValue });
      await drawElement({ path: elementPath });
    }

    saveImage(editionCount);
    generateMetadata(editionCount, attributes);
    console.log(`✅ NFT ${editionCount} généré`);
    editionCount++;
  }
};

module.exports = { buildSetup, startCreating };
