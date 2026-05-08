import { createFileRoute, Link } from '@tanstack/react-router';
import { useState } from 'react';
import { Activity } from 'lucide-react';
import { useUsers } from '@/hooks/api/use-users';
import { WorkoutSection } from '@/components/user/workout-section';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import type { DateRangeValue } from '@/components/ui/date-range-selector';

export const Route = createFileRoute('/_authenticated/workouts')({
  component: WorkoutsPage,
});

function WorkoutsPage() {
  const { data: usersResp, isLoading } = useUsers({
    page: 1,
    limit: 100,
  });
  const users = (usersResp as { items?: any[] } | undefined)?.items ?? [];
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRangeValue>(30);

  // Auto-select if there's exactly one user
  const activeUserId =
    selectedUserId ?? (users.length === 1 ? users[0].id : null);

  return (
    <div className="relative min-h-full p-6 md:p-8 space-y-6">
      <PageHeader
        icon={Activity}
        title="Workouts"
        description="All workout sessions across your users with full GPS tracks and per-sample sensor streams."
      />

      {isLoading ? (
        <div className="h-40 flex items-center justify-center">
          <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : users.length === 0 ? (
        <div className="border border-dashed border-border/60 rounded-lg p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No users yet. Create one in{' '}
            <Link to="/users" className="text-primary underline">
              Users
            </Link>
            .
          </p>
        </div>
      ) : users.length > 1 && !selectedUserId ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Choose a user:</p>
          <div className="flex flex-wrap gap-2">
            {users.map((u) => {
              const label =
                u.first_name || u.last_name
                  ? `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim()
                  : (u.email ?? u.id.slice(0, 8));
              return (
                <Button
                  key={u.id}
                  variant="outline"
                  onClick={() => setSelectedUserId(u.id)}
                >
                  {label}
                </Button>
              );
            })}
          </div>
        </div>
      ) : activeUserId ? (
        <WorkoutSection
          userId={activeUserId}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
        />
      ) : null}
    </div>
  );
}
