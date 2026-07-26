import { useState } from 'react';
import { History, Receipt } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Table, THead, TBody, Th, Tr, Td, EmptyRow, SymbolCell } from '../ui/DataTable';
import Skeleton, { SkeletonNumber } from '../ui/Skeleton';
import Badge from '../ui/Badge';
import { statusTone } from '../../lib/statusTone';
import Tabs from '../ui/Tabs';
import EmptyState from '../ui/EmptyState';
import { inr, qty as fmtQty, dateTime, shortId, EM_DASH } from '../../lib/format';

const TABS = [
  { id: 'trades', label: 'Trades' },
  { id: 'orders', label: 'Orders' },
];

function LoadingRows({ columns, count = 3 }) {
  return Array.from({ length: count }, (_, index) => `history-skeleton-${index}`).map((key) => (
    <Tr key={key}>
      {columns.map((column, columnIndex) => (
        <Td key={column.key} numeric={column.numeric}>
          {column.numeric ? (
            <SkeletonNumber width={64} />
          ) : (
            <Skeleton width={columnIndex === 0 ? 70 : 100} height={13} />
          )}
        </Td>
      ))}
    </Tr>
  ));
}

const TRADE_COLUMNS = [
  { key: 'symbol', label: 'Instrument', numeric: false, width: 150 },
  { key: 'side', label: 'Side', numeric: false, width: 80 },
  { key: 'qty', label: 'Qty', numeric: true, width: 80 },
  { key: 'price', label: 'Price', numeric: true, width: 120 },
  { key: 'value', label: 'Value', numeric: true, width: 130 },
  { key: 'time', label: 'Executed', numeric: false, width: 170 },
  { key: 'id', label: 'Trade ID', numeric: false, width: 120 },
];

function TradesTable({ trades, isLoading }) {
  return (
    <Table>
      <THead>
        <tr>
          {TRADE_COLUMNS.map((column) => (
            <Th key={column.key} numeric={column.numeric} width={column.width}>
              {column.label}
            </Th>
          ))}
        </tr>
      </THead>
      <TBody>
        {isLoading ? <LoadingRows columns={TRADE_COLUMNS} /> : null}

        {!isLoading && trades.length === 0 ? (
          <EmptyRow colSpan={TRADE_COLUMNS.length}>
            <EmptyState
              compact
              icon={<Receipt size={20} strokeWidth={1.8} />}
              title="No trades yet"
              description="Executed trades will appear here."
            />
          </EmptyRow>
        ) : null}

        {!isLoading &&
          trades.map((trade, index) => (
            <Tr key={trade.trade_id ?? index}>
              <Td>
                <SymbolCell symbol={trade.symbol} />
              </Td>
              <Td>
                <Badge tone={trade.side === 'BUY' ? 'profit' : 'loss'}>{trade.side}</Badge>
              </Td>
              <Td numeric>{fmtQty(trade.quantity)}</Td>
              <Td numeric muted>
                {inr(trade.price)}
              </Td>
              <Td numeric>{inr(trade.total_value)}</Td>
              <Td muted>{dateTime(trade.timestamp)}</Td>
              <Td tertiary>{shortId(trade.trade_id, 10)}</Td>
            </Tr>
          ))}
      </TBody>
    </Table>
  );
}

const ORDER_COLUMNS = [
  { key: 'symbol', label: 'Instrument', numeric: false, width: 150 },
  { key: 'side', label: 'Side', numeric: false, width: 80 },
  { key: 'qty', label: 'Qty', numeric: true, width: 80 },
  { key: 'status', label: 'Status', numeric: false, width: 110 },
  { key: 'price', label: 'Fill price', numeric: true, width: 120 },
  { key: 'time', label: 'Placed', numeric: false, width: 170 },
  { key: 'id', label: 'Order ID', numeric: false, width: 120 },
];

function OrdersTable({ orders, isLoading }) {
  return (
    <Table>
      <THead>
        <tr>
          {ORDER_COLUMNS.map((column) => (
            <Th key={column.key} numeric={column.numeric} width={column.width}>
              {column.label}
            </Th>
          ))}
        </tr>
      </THead>
      <TBody>
        {isLoading ? <LoadingRows columns={ORDER_COLUMNS} /> : null}

        {!isLoading && orders.length === 0 ? (
          <EmptyRow colSpan={ORDER_COLUMNS.length}>
            <EmptyState
              compact
              icon={<History size={20} strokeWidth={1.8} />}
              title="No orders yet"
              description="Orders you place will be listed here with their status."
            />
          </EmptyRow>
        ) : null}

        {!isLoading &&
          orders.map((order, index) => (
            <Tr key={order.order_id ?? index}>
              <Td>
                <SymbolCell symbol={order.symbol} />
              </Td>
              <Td>
                <Badge tone={order.side === 'BUY' ? 'profit' : 'loss'}>{order.side}</Badge>
              </Td>
              <Td numeric>{fmtQty(order.quantity)}</Td>
              <Td>
                <Badge tone={statusTone(order.status)}>{order.status}</Badge>
              </Td>
              <Td numeric muted>
                {order.price ? inr(order.price) : EM_DASH}
              </Td>
              <Td muted>{dateTime(order.timestamp)}</Td>
              <Td tertiary>{shortId(order.order_id, 10)}</Td>
            </Tr>
          ))}
      </TBody>
    </Table>
  );
}

export default function HistoryPanel({ trades = [], orders = [], isTradesLoading = false, isOrdersLoading = false }) {
  const [tab, setTab] = useState('trades');

  const count = tab === 'trades' ? trades.length : orders.length;
  const loading = tab === 'trades' ? isTradesLoading : isOrdersLoading;

  return (
    <Card>
      <CardHeader
        title="Activity"
        subtitle={loading ? 'Loading…' : `${count} ${tab === 'trades' ? 'trade' : 'order'}${count === 1 ? '' : 's'}`}
        actions={<Tabs items={TABS} value={tab} onChange={setTab} ariaLabel="History type" />}
      />
      <CardBody flush>
        {tab === 'trades' ? (
          <TradesTable trades={trades} isLoading={isTradesLoading} />
        ) : (
          <OrdersTable orders={orders} isLoading={isOrdersLoading} />
        )}
      </CardBody>
    </Card>
  );
}
