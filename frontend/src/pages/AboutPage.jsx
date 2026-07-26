import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { SingleLayout } from '../components/layout/AppShell';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import { PATCH_NOTES } from '../data/patchNotes';
import styles from './AboutPage.module.css';

const LAYERS = [
  {
    name: 'Domain',
    tag: 'quantnest/domain',
    description:
      'Entities, value objects and business rules: Wallet, Portfolio, Order, Trade and the execution engine. Pure logic with no web or database concerns.',
  },
  {
    name: 'Application',
    tag: 'quantnest/application',
    description:
      'CQRS orchestration: commands and handlers for writes, query services for reads. Coordinates the domain without knowing about HTTP.',
  },
  {
    name: 'Infrastructure',
    tag: 'quantnest/infra',
    description:
      'Persistence and external integrations — the storage layer and market data provider that back the domain ports.',
  },
  {
    name: 'API',
    tag: 'quantnest/api',
    description:
      'FastAPI presentation layer: routing, request validation, dependency injection and error translation.',
  },
];

const TRADE_FLOW = `POST /portfolio/{wallet_id}/buy
  └─ application/handlers → BuyAssetHandler.handle(command)
      └─ domain/order_engine → OrderExecutionEngine.place_order(MARKET)
          ├─ MarketProvider.get_price(symbol)          → live LTP
          ├─ validate: Portfolio.cash() >= quantity × price
          ├─ Wallet.debit(cost, transaction_id)        → FundsDebited event
          ├─ Portfolio positions updated
          └─ Order marked FILLED, Trade recorded`;

const CATEGORY_TONES = {
  FEAT: 'profit',
  FIX: 'loss',
  ARCH: 'info',
};

function Release({ patch, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={styles.release}>
      <button type="button" className={styles.releaseHead} onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={14} strokeWidth={2} /> : <ChevronRight size={14} strokeWidth={2} />}
        <Badge tone="info">{patch.version}</Badge>
        <span className={styles.releaseTitle}>{patch.title}</span>
        <span className={styles.releaseDate}>{patch.date}</span>
      </button>

      {open ? (
        <div className={styles.releaseBody}>
          {patch.changes.map((change) => (
            <div className={styles.changeGroup} key={change.category}>
              <Badge tone={CATEGORY_TONES[change.category] ?? 'neutral'}>{change.category}</Badge>
              <div className={styles.changeList}>
                {change.items.map((item) => (
                  <p className={styles.changeItem} key={item}>
                    {item}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function AboutPage() {
  const latest = PATCH_NOTES[0];

  return (
    <SingleLayout>
      <Card>
        <CardHeader
          title="Architecture"
          subtitle="Domain-driven design with a CQRS application layer"
        />
        <CardBody>
          <div className={styles.layerGrid}>
            {LAYERS.map((layer) => (
              <div className={styles.layer} key={layer.name}>
                <span className={styles.layerName}>{layer.name}</span>
                <span className={styles.layerTag}>{layer.tag}</span>
                <span className={styles.layerDesc}>{layer.description}</span>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Trade execution flow" subtitle="How a market buy travels through the layers" />
        <CardBody>
          <pre className={styles.flow}>{TRADE_FLOW}</pre>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Release history"
          subtitle={`Current version ${latest.version} · ${latest.date}`}
        />
        <CardBody>
          <div className={styles.releases}>
            {PATCH_NOTES.map((patch, index) => (
              <Release key={patch.version} patch={patch} defaultOpen={index === 0} />
            ))}
          </div>
        </CardBody>
      </Card>

      <p className={styles.footer}>QuantNest {latest.version} · Trading simulator for education and research</p>
    </SingleLayout>
  );
}
