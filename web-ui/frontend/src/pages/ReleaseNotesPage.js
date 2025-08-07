import React from 'react';
import ReleaseNotes from '../components/ReleaseNotes';
import { releaseNotes } from '../data/releaseNotes';

const ReleaseNotesPage = () => {
  return (
    <div className="bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Release Notes</h1>
          <p className="text-gray-600">
            Stay up to date with the latest features and improvements
          </p>
        </header>
        
        <div className="space-y-4">
          {releaseNotes.map(release => (
            <ReleaseNotes
              key={release.id}
              version={release.version}
              date={release.date}
              title={release.title}
              summary={release.summary}
              highlights={release.highlights}
              details={release.details}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReleaseNotesPage;