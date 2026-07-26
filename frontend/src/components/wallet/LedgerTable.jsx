import { Receipt } from 'lucide-react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Table, THead, TBody, Th, Tr, Td, EmptyRow } from '../ui/DataTable';
import Skeleton, { SkeletonNumber } from '../ui/Skeleton';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import EmptyState from '../ui/EmptyState';
import { inrSigned, dateTime, shortId } from '../../lib/format';
import { RefreshCw } from 'lucide-react';

const COLUMNS = [
  { key: 'time', label: 'Timestamp', numeric: false, width: 180 },
  { key: 'type', label: 'Event', numeric: false, width: 150 },
  { key: 'amount', label: 'Amount', numeric: true, width: 140 },
  { key: 'txId', label: 'Transaction ID', numeric: false, width: 200 },
];

const EVENT_LABELS = {
  FundsCredited: 'Credit',
  FundsDebited: 'Debit',
};

export default function LedgerTable({ events = [], isLoading = false, isFetching = false, onRefresh }) {
  return (
    <Card>
      <CardHeader
        title="Ledger"
        subtitle={
          isLoading ? 'Loading events…' : `${events.length} event${events.length === 1 ? '' : 's'}`
        }
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            loading={isFetching}
            leftIcon={!isFetching ? <RefreshCw size={14} strokeWidth={2} /> : null}
          >
            Refresh
          </Button>
        }
      />

      <CardBody flush>
        <Table>
          <THead>
            <tr>
              {COLUMNS.map((column) => (
                <Th key={column.key} numeric={column.numeric} width={column.width}>
                  {column.label}
                </Th>
              ))}
            </tr>
          </THead>

          <TBody>
            {isLoading
              ? ['a', 'b', 'c', 'd'].map((key) => (
                  <Tr key={`ledger-skeleton-${key}`}>
                    <Td>
                      <Skeleton width={130} height={13} />
                    </Td>
                    <Td>
                      <Skeleton width={64} height={16} variant="block" />
                    </Td>
                    <Td numeric>
                      <SkeletonNumber width={80} />
                    </Td>
                    <Td>
                      <Skeleton width={140} height={11} />
                    </Td>
                  </Tr>
                ))
              : null}

            {!isLoading && events.length === 0 ? (
              <EmptyRow colSpan={COLUMNS.length}>
                <EmptyState
                  icon={<Receipt size={20} strokeWidth={1.8} />}
                  title="No ledger events"
                  description="Credit funds to your wallet to get started."
                />
              </EmptyRow>
            ) : null}

            {!isLoading &&
              events.map((event, index) => {
                const isCredit = event.event_type === 'FundsCredited';
                const amount = isCredit ? event.amount : -Math.abs(event.amount);

                return (
                  <Tr key={event.event_id ?? index}>
                    <Td muted>{dateTime(event.timestamp)}</Td>
                    <Td>
                      <Badge tone={isCredit ? 'profit' : 'loss'}>
                        {EVENT_LABELS[event.event_type] ?? event.event_type}
                      </Badge>
                    </Td>
                    <Td numeric tone={isCredit ? 'profit' : 'loss'}>
                      {inrSigned(amount)}
                    </Td>
                    <Td tertiary>{shortId(event.transaction_id, 18)}</Td>
                  </Tr>
                );
              })}
          </TBody>
        </Table>
      </CardBody>
    </Card>
  );
}
