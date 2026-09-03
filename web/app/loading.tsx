import React from 'react';
import { Skeleton } from './components/primitives';

export default function Loading() {
  return (
    <div className="stack" aria-busy>
      <Skeleton h={14} w={120} />
      <Skeleton h={34} w="52%" />
      <div className="kpi-strip with-hero" style={{ marginTop: '1.5rem' }}>
        <Skeleton h={132} />
        <Skeleton h={132} />
        <Skeleton h={132} />
      </div>
      <Skeleton h={280} style={{ marginTop: '1.5rem' }} />
    </div>
  );
}
