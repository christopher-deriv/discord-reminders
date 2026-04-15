import { useState, useEffect } from 'react';
import {
  format,
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  isSameMonth,
  isSameDay,
  addDays
} from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { DiscordSDK } from '@discord/embedded-app-sdk';

interface EventData {
  title: string;
  time: string;
  color: string;
}

type EventsMap = Record<string, EventData[]>;

// Initialize safely avoiding crashing if frame_id is missing during local/mock dev
let discordSdk: DiscordSDK | null = null;
try {
  discordSdk = new DiscordSDK(import.meta.env.VITE_DISCORD_CLIENT_ID || '1234567890');
} catch (e) {
  console.warn("Discord SDK failed to init, using mock mode.", e);
}

function App() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [events, setEvents] = useState<EventsMap>({});
  const [, setLoading] = useState(true);
  const [auth, setAuth] = useState<any>(null);

  useEffect(() => {
    async function setupDiscordSdk() {
      // If we are not in an iframe (e.g. running directly via Vite preview or Playwright), skip SDK and use fallback
      if (!discordSdk || window.parent === window || window.location.search.includes('mock=true')) {
        setAuth({ user: { username: "Dev User" }, access_token: "mock-token" });
        return;
      }
      try {
        await discordSdk.ready();

        // Authorize with Discord Client
        const { code } = await discordSdk.commands.authorize({
          client_id: import.meta.env.VITE_DISCORD_CLIENT_ID || '1234567890',
          response_type: "code",
          state: "",
          prompt: "none",
          scope: ["identify", "guilds"]
        });

        // Exchange code for token via our backend
        const response = await fetch("/api/token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code })
        });
        const { access_token } = await response.json();

        // Authenticate the embedded app
        const authResult = await discordSdk.commands.authenticate({
          access_token
        });

        setAuth(authResult);
      } catch (e) {
        console.error("Discord SDK Error:", e);
        // Fallback for local development outside Discord
        setAuth({ user: { username: "Dev User" }, access_token: "mock-token" });
      }
    }
    setupDiscordSdk();
  }, []);

  useEffect(() => {
    async function fetchReminders() {
      if (!auth) return;

      try {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth() + 1; // 1-12

        // Fetch from backend API
        const res = await fetch(`/api/reminders?year=${year}&month=${month}`, {
          headers: {
            'Authorization': `Bearer ${auth.access_token || 'dev-token'}`
          }
        });
        const data = await res.json();

        if (window.location.search.includes('mock=true') && Object.keys(data.events || {}).length === 0) {
            // Provide a mock event if the database is empty in mock mode
            const mockEvents: EventsMap = {};
            const dateStr = format(new Date(year, month - 1, 24), 'yyyy-MM-dd');
            mockEvents[dateStr] = [{ title: 'Team Sync', time: '10:25 - 11:20', color: '#4da6ff' }];
            setEvents(mockEvents);
        } else {
            setEvents(data.events || {});
        }
      } catch (e) {
        console.error("Failed to fetch reminders:", e);
      } finally {
        setLoading(false);
      }
    }
    fetchReminders();
  }, [currentMonth, auth]);

  const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));
  const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const onDateClick = (day: Date) => setSelectedDate(day);

  // Calendar rendering logic
  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);

  const dateFormat = "d";
  const rows = [];
  let days = [];
  let day = startDate;
  let formattedDate = "";

  while (day <= endDate) {
    for (let i = 0; i < 7; i++) {
      formattedDate = format(day, dateFormat);
      const cloneDay = day;
      const dateKey = format(cloneDay, 'yyyy-MM-dd');
      const dayEvents = events[dateKey];
      const isSelected = isSameDay(day, selectedDate);
      const isCurrentMonth = isSameMonth(day, monthStart);

      days.push(
        <div
          key={day.toString()}
          onClick={() => onDateClick(cloneDay)}
          className={`relative flex flex-col items-center justify-center p-2 rounded-lg cursor-pointer h-12 w-12 mx-auto
            ${!isCurrentMonth ? 'text-gray-300' : 'text-gray-700'}
            ${isSelected ? 'bg-gray-900 text-white shadow-md' : 'hover:bg-gray-200 bg-gray-100'}
          `}
        >
          <span className="font-medium">{formattedDate}</span>
          {dayEvents && dayEvents.length > 0 && (
            <span
              className="absolute bottom-1 w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: dayEvents[0].color }}
            />
          )}
        </div>
      );
      day = addDays(day, 1);
    }
    rows.push(
      <div className="grid grid-cols-7 gap-2 mb-2" key={day.toString()}>
        {days}
      </div>
    );
    days = [];
  }

  // Days header
  const daysHeader = ['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
    <div key={i} className="text-gray-400 font-medium text-center h-8 flex items-center justify-center">
      {d}
    </div>
  ));

  // Upcoming Events list
  // Find all events from selectedDate onwards in the current month
  const upcomingEvents = Object.keys(events)
    .filter(dateStr => new Date(dateStr) >= selectedDate)
    .sort()
    .flatMap(dateStr => events[dateStr].map(ev => ({ ...ev, dateStr })));

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4 font-sans app-container">
      <div className="bg-white rounded-2xl shadow-xl flex flex-col md:flex-row overflow-hidden max-w-4xl w-full border border-gray-100">

        {/* Left Pane - Calendar */}
        <div className="p-8 flex-1 border-b md:border-b-0 md:border-r border-gray-100">

          <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-2 mb-6">
            <button onClick={prevMonth} className="p-1 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors">
              <ChevronLeft size={20} />
            </button>
            <h2 className="text-lg font-semibold text-gray-800">
              {format(currentMonth, "MMMM yyyy")}
            </h2>
            <button onClick={nextMonth} className="p-1 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors">
              <ChevronRight size={20} />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-2 mb-4 calendar-grid">
            {daysHeader}
          </div>
          <div>
            {rows}
          </div>
        </div>

        {/* Right Pane - Details */}
        <div className="p-8 w-full md:w-80 bg-white">
          <h3 className="text-gray-900 font-semibold mb-1">
            {format(selectedDate, "MMMM d, eeee")}
          </h3>
          <p className="text-gray-400 text-sm mb-6">Today</p>

          <div className="space-y-6">
            {upcomingEvents.length === 0 ? (
              <p className="text-gray-500 text-sm">No upcoming events.</p>
            ) : (
              upcomingEvents.map((ev, i) => {
                const evDate = new Date(ev.dateStr);
                const isSelectedDate = isSameDay(evDate, selectedDate);
                // Grouping roughly: if it's the selected date, put it top. Else under "Upcoming"
                // For simplicity, just list them all here for now.
                return (
                  <div key={i} className="flex gap-4">
                    <div className="w-10 h-10 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
                      <CalendarIcon size={20} className="text-gray-400" />
                    </div>
                    <div>
                      <h4 className="text-gray-900 font-medium flex items-center gap-2">
                        {ev.title}
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ev.color }} />
                      </h4>
                      <p className="text-gray-400 text-sm">
                        {!isSelectedDate && `${format(evDate, "MMM d")} • `}
                        {ev.time}
                      </p>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
