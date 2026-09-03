import React from 'react';
import { SectionHeader, Button } from './components/primitives';

export default function NotFound() {
  return (
    <div>
      <SectionHeader kicker="404" title="That page isn't here" description="The link may be stale, or the route moved when the dashboard was reorganised around the result." />
      <Button href="/" variant="quiet">Back to the result</Button>
    </div>
  );
}
