# NFT individuals page

Read-only page that lists every individual known to the Wildbook server and links each one to an
edition of the "Las Guacamayas" NFT collection. Nothing is minted: links and filled metadata are off-chain.

## Views

All three are served by the same `index.html`; the path picks the view, and the header links switch between them.

| Path | View | Shows |
|---|---|---|
| `/` | Both | Each Wildbook individual (photo, species, encounters, dates) next to its linked NFT |
| `/individuals` | Individuals | The individuals only, without NFTs |
| `/nfts` | NFTs | Every edition of the collection, with its traits and the individual it is linked to (or free) |

Every view can be filtered by species. JSON behind them: `/api/individuals` (Both, Individuals) and `/api/nfts` (NFTs).

## Files

- `server.py`: Python standard library only. Serves `index.html`, `/api/individuals`, `/api/nfts`,
  `/collection/...` and `/nft/<edition>.json` on port 8090. Reads the OpenSearch indices `individual`
  and `encounter` on `127.0.0.1:9200`; never writes to Wildbook or OpenSearch.
- Linking: every 60 s, any individual not yet in `links.json` gets the lowest free edition, keyed by its
  Wildbook individual id. Links are never reassigned. `links.json` is runtime state (git-ignored).
- `collection/`: 19 editions (0–18) generated with `Hashlips/V4`: `images/` (3000 px PNG), `thumbs/` (WebP),
  `json/` (HashLips metadata; `/nft/<edition>.json` fills `extensions.ara_id` etc. from the link).
- `deploy/nft-individuals.service`: systemd unit as installed on the server.

## Running on the server

Currently deployed from `/opt/wildme/nft` on 65.108.33.121: http://65.108.33.121:8090/ (Both), http://65.108.33.121:8090/individuals, http://65.108.33.121:8090/nfts.

```sh
cp -r nft-individuals /opt/wildme/nft
cp /opt/wildme/nft/deploy/nft-individuals.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now nft-individuals
```

Wildbook returns image URLs starting with `http://localhost:81` (asset store web root left from the dev
config); `server.py` rewrites them to the public host.
