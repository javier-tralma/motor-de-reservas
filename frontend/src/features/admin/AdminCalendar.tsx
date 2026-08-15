import 'temporal-polyfill/global';
import React, { useRef, useEffect, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import type { CalendarRef, DatesSetInfo, EventClickInfo } from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import listPlugin from '@fullcalendar/react/list';
import type { CalendarEventItem } from '../../lib/api/admin';
import { formatCivilDateInTimezone } from '../../lib/format/date';
import { mapCalendarEventsToFullCalendar } from './adminCalendarUtils';

interface AdminCalendarProps {
  events: CalendarEventItem[];
  timezone: string;
  onDatesSet: (start: string, end: string) => void;
  onEventClick: (kind: string, id: string) => void;
  userSelectedView: string | null;
  onViewChange: (view: string) => void;
}

const VIEW_MOBILE = 'listWeek';
const VIEW_DESKTOP = 'timeGridWeek';
const MOBILE_BREAKPOINT = 768;

export const AdminCalendar: React.FC<AdminCalendarProps> = ({
  events,
  timezone,
  onDatesSet,
  onEventClick,
  userSelectedView,
  onViewChange,
}) => {
  const calendarRef = useRef<CalendarRef | null>(null);
  const isInitialMount = useRef(true);
  const isResizeTriggered = useRef(false);
  const currentViewRef = useRef<string>(
    userSelectedView ||
      (typeof window !== 'undefined' && window.innerWidth < MOBILE_BREAKPOINT ? VIEW_MOBILE : VIEW_DESKTOP)
  );

  const handleDatesSet = useCallback(
    (arg: DatesSetInfo) => {
      const startCivil = formatCivilDateInTimezone(arg.start, timezone);
      const endCivil = formatCivilDateInTimezone(arg.end, timezone);
      onDatesSet(startCivil, endCivil);

      if (isInitialMount.current) {
        isInitialMount.current = false;
        currentViewRef.current = arg.view.type;
        return;
      }

      if (isResizeTriggered.current) {
        isResizeTriggered.current = false;
        currentViewRef.current = arg.view.type;
        return;
      }

      // If view changed via user interaction (e.g. clicking toolbar buttons)
      if (arg.view.type !== currentViewRef.current) {
        currentViewRef.current = arg.view.type;
        onViewChange(arg.view.type);
      }
    },
    [timezone, onDatesSet, onViewChange]
  );

  const handleEventClick = useCallback(
    (info: EventClickInfo) => {
      const extendedProps = info.event.extendedProps as {
        kind?: 'booking' | 'time_off';
        id?: string;
      };
      if (extendedProps.kind === 'booking' && extendedProps.id) {
        onEventClick('booking', extendedProps.id);
      }
      // time_off clicks are strictly ignored to prevent any navigation
    },
    [onEventClick]
  );

  useEffect(() => {
    if (userSelectedView && calendarRef.current) {
      const calApi = calendarRef.current.getApi();
      if (calApi && calApi.view.type !== userSelectedView) {
        calApi.changeView(userSelectedView);
      }
    }
  }, [userSelectedView]);

  useEffect(() => {
    const handleResize = () => {
      if (userSelectedView) return; // Respect user's explicit view choice

      const calApi = calendarRef.current?.getApi();
      if (!calApi) return;

      const isMobile = window.innerWidth < MOBILE_BREAKPOINT;
      const targetView = isMobile ? VIEW_MOBILE : VIEW_DESKTOP;

      if (calApi.view.type !== targetView) {
        isResizeTriggered.current = true;
        calApi.changeView(targetView);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [userSelectedView]);

  const fcEvents = mapCalendarEventsToFullCalendar(events);

  return (
    <FullCalendar
      ref={calendarRef}
      plugins={[timeGridPlugin, listPlugin]}
      initialView={
        userSelectedView ||
        (typeof window !== 'undefined' && window.innerWidth < MOBILE_BREAKPOINT ? VIEW_MOBILE : VIEW_DESKTOP)
      }
      headerToolbar={{
        left: 'prev,next today',
        center: 'title',
        right: 'timeGridDay,timeGridWeek,listWeek',
      }}
      allDaySlot={false}
      slotMinTime="07:00:00"
      slotMaxTime="22:00:00"
      locale="es"
      events={fcEvents}
      datesSet={handleDatesSet}
      eventClick={handleEventClick}
      height="100%"
      editable={false}
      droppable={false}
      eventStartEditable={false}
      eventDurationEditable={false}
      selectable={false}
      timeZone={timezone}
    />
  );
};
