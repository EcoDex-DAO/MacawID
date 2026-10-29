const basePath = process.cwd();
const { MODE } = require(`${basePath}/constants/blend_mode.js`);
const { NETWORK } = require(`${basePath}/constants/network.js`);

const network = NETWORK.sol;

const namePrefix = "Las Guacamayas";
const description = "Un Ara de la collection QuipEcos, inspiré des cultures préhispaniques et du travail de protection.";
const baseUri = "ipfs://NewUriToReplace"; // URI IPFS des images

const solanaMetadata = {
  symbol: "LGM",
  seller_fee_basis_points: 300, // 3%
  external_url: "https://www.quipecos.com/",
  collection: {
    name: "QuipEcos - Guacamayas",
    family: "QuipEcos Collection",
  },
  creators: [
    {
      address: "<DAO_MULTISIG_WALLET>",
      share: 100,
    },
  ],
};

const layerConfigurations = [
  {
    growEditionSizeTo: 5,
    layersOrder: [
      { name: "Background" },
      { name: "Plumage" },
      { name: "Eye" },
      { name: "Beak" },
      { name: "Clothe" },
      { name: "Hat" },
      { name: "Accessory" },
    ],
  },
];

const shuffleLayerConfigurations = false;
const debugLogs = false;

const format = {
  width: 3000,
  height: 3000,
  smoothing: false,
};

const extraMetadata = {
  extensions: {
    ara_id: null,
    ara_name: null,
    id_source: "general",
    id_proof_uri: null,
    notes: null,
    linked_at: null,
    named_at: null,
    last_modified: null,
    updater: null,
  },
};

const rarityDelimiter = "#";
const uniqueDnaTorrance = 10000;

const preview = {
  thumbPerRow: 5,
  thumbWidth: 50,
  imageRatio: format.height / format.width,
  imageName: "preview.png",
};

module.exports = {
  format,
  baseUri,
  description,
  background: {
    generate: true,
    brightness: "80%",
    static: false,
    default: "#ffffff",
  },
  uniqueDnaTorrance,
  layerConfigurations,
  rarityDelimiter,
  preview,
  shuffleLayerConfigurations,
  debugLogs,
  extraMetadata,
  namePrefix,
  network,
  solanaMetadata,
};
