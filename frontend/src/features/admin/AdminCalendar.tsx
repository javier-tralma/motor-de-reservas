import 'temporal-polyfill/global';
import React, { useRef, useEffect, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import type { CalendarRef, DatesSetInfo, EventClickInfo } from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import listPlugin from '@fullcalendar/react/list';
import classicThemePlugin from '@fullcalendar/react/themes/classic';
import '@fullcalendar/react/skeleton.css';
import '@fullcalendar/react/themes/classic/theme.css';
import '@fullcalendar/react/themes/classic/palette.css';
import type { CalendarEventItem } from '../../lib/api/admin';
import { formatCivilDateInTimezone } from '../../lib/format/date';
import {
  mapCalendarEventsToFullCalendar,
  formatShortCustomerName,
} from './adminCalendarUtils';

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

  const renderEventContent = (eventInfo: {
    event: {
      title: string;
      start: Date | null;
      end: Date | null;
      extendedProps: {
        kind?: 'booking' | 'time_off';
        provider_name?: string;
        booking_status?: string | null;
        booking_status_label?: string;
        customer_display_name?: string | null;
        customer_short_name?: string | null;
        service_name?: string | null;
        reason?: string | null;
      };
    };
    timeText: string;
    isShort?: boolean;
    view: { type: string };
  }) => {
    const { event, timeText, isShort: fcIsShort, view } = eventInfo;
    const isListView = view?.type?.startsWith('list');
    const isTimeOff = event.extendedProps?.kind === 'time_off';
    const statusLabel = event.extendedProps?.booking_status_label;
    const customer = event.extendedProps?.customer_display_name;
    const service = event.extendedProps?.service_name;
    const provider = event.extendedProps?.provider_name;
    const reason = event.extendedProps?.reason;

    // Calculate duration in minutes when available
    const durationMinutes =
      event.start && event.end
        ? Math.round((event.end.getTime() - event.start.getTime()) / 60000)
        : 30;
    const isShort = fcIsShort || durationMinutes <= 30;

    if (isListView) {
      if (isTimeOff) {
        return (
          <div className="flex flex-col gap-0.5 py-0.5 leading-snug text-xs select-none">
            {timeText && <span className="font-mono text-[11px] text-[#66736e]">{timeText}</span>}
            <span className="font-semibold text-[#1f2a27]">Bloqueo{provider ? `: ${provider}` : ''}</span>
            {reason && <span className="text-[11px] text-[#66736e] whitespace-normal break-words">{reason}</span>}
          </div>
        );
      }

      return (
        <div className="flex flex-col gap-0.5 py-0.5 leading-snug text-xs select-none">
          {timeText && <span className="font-mono text-[11px] text-[#66736e]">{timeText}</span>}
          <span className="font-semibold text-[#1f2a27]">
            [{statusLabel || 'Reserva'}]{provider ? ` ${provider}` : ''}
          </span>
          <span className="text-xs text-[#1f2a27]">{customer || 'Cliente'}</span>
          {service && <span className="text-[11px] text-[#66736e]">{service}</span>}
        </div>
      );
    }

    // Grid views (timeGridWeek, timeGridDay)
    if (isTimeOff) {
      if (isShort) {
        return (
          <div className="flex flex-col h-full overflow-hidden text-white leading-tight p-1 select-none justify-center gap-0.5">
            {timeText && <span className="font-mono text-[10px] opacity-90">{timeText}</span>}
            <div className="font-bold text-[11px] truncate">
              Bloqueo{provider ? `: ${provider}` : ''}
            </div>
          </div>
        );
      }

      return (
        <div className="flex flex-col h-full overflow-hidden text-white leading-tight p-1 select-none gap-0.5">
          {timeText && <span className="font-mono text-[10px] opacity-90">{timeText}</span>}
          <div className="font-bold text-[11px] leading-snug whitespace-normal break-words">
            Bloqueo{provider ? `: ${provider}` : ''}
          </div>
          {reason && (
            <div className="text-[11px] opacity-95 whitespace-normal break-words leading-snug mt-0.5">
              {reason}
            </div>
          )}
        </div>
      );
    }

    // Booking in Grid Views
    if (isShort) {
      const shortCustomer =
        event.extendedProps?.customer_short_name ||
        formatShortCustomerName(customer);

      return (
        <div className="flex flex-col h-full overflow-hidden text-white leading-tight p-1 select-none justify-between">
          {timeText && <span className="font-mono text-[10px] opacity-90">{timeText}</span>}
          <div className="font-bold text-[11px] leading-tight">
            [{statusLabel || 'Reserva'}]
          </div>
          <div className="text-[11px] font-medium leading-tight">
            {shortCustomer}
          </div>
        </div>
      );
    }

    // Long Booking in Grid Views (> 30 min)
    return (
      <div className="flex flex-col h-full overflow-hidden text-white leading-tight p-1 select-none gap-0.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          {timeText && <span className="font-mono text-[10px] opacity-90 shrink-0">{timeText}</span>}
          <span className="font-bold text-[11px] truncate">
            [{statusLabel || 'Reserva'}]{provider ? ` ${provider}` : ''}
          </span>
        </div>
        <div className="text-[11px] font-semibold leading-tight truncate">
          {customer || 'Cliente'}
        </div>
        {service && (
          <div className="text-[10px] opacity-90 leading-tight truncate">
            {service}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fc h-full">
      <FullCalendar
        ref={calendarRef}
        plugins={[timeGridPlugin, listPlugin, classicThemePlugin]}
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
        eventMinHeight={48}
        eventShortHeight={50}
        locale="es"
        events={fcEvents}
        datesSet={handleDatesSet}
        eventClick={handleEventClick}
        eventContent={renderEventContent}
        eventDidMount={(info) => {
          const accessibleLabel =
            (info.event.extendedProps as { accessible_label?: string })?.accessible_label ||
            info.event.title;
          const fullAccessibleLabel = info.timeText
            ? `${accessibleLabel} (${info.timeText})`
            : accessibleLabel;
          if (fullAccessibleLabel) {
            info.el.setAttribute('aria-label', fullAccessibleLabel);
            info.el.setAttribute('title', fullAccessibleLabel);
          }
        }}
        height="auto"
        editable={false}
        droppable={false}
        eventStartEditable={false}
        eventDurationEditable={false}
        selectable={false}
        timeZone={timezone}
      />
    </div>
  );
};
