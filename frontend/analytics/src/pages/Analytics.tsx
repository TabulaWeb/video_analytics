import { useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  Container,
  Grid,
  Heading,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  VStack,
  Text,
  useToast,
  Icon,
  Flex,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Spinner,
  Center,
} from '@chakra-ui/react';
import { FaChartBar, FaSignOutAlt, FaDownload, FaChevronDown, FaChartLine, FaCalendarAlt, FaClock, FaExclamationCircle } from 'react-icons/fa';
import 'chart.js/auto';
import { type ChartOptions } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { useAuth } from '../contexts/AuthContext';
import { statsAPI, exportAPI, streamAPI } from '../services/api';
import StreamPlayer from '../components/StreamPlayer';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const CHART_COLORS = {
  in: 'rgb(72, 187, 120)',   // green.500
  out: 'rgb(245, 101, 101)', // red.500
  grid: 'rgba(0, 0, 0, 0.06)',
};

const barChartOptions: ChartOptions<'bar'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const },
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.96)',
      titleColor: '#1a202c',
      bodyColor: '#4a5568',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: 12,
      displayColors: true,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxRotation: 45, minRotation: 45, font: { size: 11 } },
    },
    y: {
      beginAtZero: true,
      grid: { color: CHART_COLORS.grid },
    },
  },
};

const lineChartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const },
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.96)',
      titleColor: '#1a202c',
      bodyColor: '#4a5568',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: 12,
      displayColors: true,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxRotation: 45, minRotation: 45, font: { size: 11 } },
    },
    y: {
      beginAtZero: true,
      grid: { color: CHART_COLORS.grid },
    },
  },
};

interface PeriodStats {
  period: string;
  start_date: string;
  end_date: string;
  in_count: number;
  out_count: number;
  net_flow: number;
  total_events: number;
}

interface HourlyStats {
  hour: number;
  in_count: number;
  out_count: number;
}

interface DailyStats {
  date: string;
  IN: number;
  OUT: number;
}

interface MonthlyStats {
  month: string;
  IN: number;
  OUT: number;
}

interface PeakHourAnalytics {
  peak_hour: number | null;
  avg_count: number;
  total_count: number;
}

interface WeekdayStats {
  weekday: string;
  IN: number;
  OUT: number;
  total: number;
}

interface Averages {
  avg_per_day: number;
  avg_per_week: number;
  avg_per_month: number;
}

interface GrowthTrend {
  week_change_percent: number;
  month_change_percent: number;
  trend: 'up' | 'down' | 'stable';
}

interface PeakPrediction {
  predicted_hour: number | null;
  hours_until: number;
  expected_count: number;
  confidence: number;
}

interface CurrentStats {
  in_count: number;
  out_count: number;
  active_tracks: number;
  camera_status: string;
  fps: number;
}

export default function Analytics() {
  const { logout } = useAuth();
  const [currentStats, setCurrentStats] = useState<CurrentStats | null>(null);
  const [dayStats, setDayStats] = useState<PeriodStats | null>(null);
  const [weekStats, setWeekStats] = useState<PeriodStats | null>(null);
  const [monthStats, setMonthStats] = useState<PeriodStats | null>(null);
  const [hourlyStats, setHourlyStats] = useState<HourlyStats[]>([]);
  const [dailyTrendStats, setDailyTrendStats] = useState<DailyStats[]>([]);
  const [monthlyTrendStats, setMonthlyTrendStats] = useState<MonthlyStats[]>([]);
  const [peakHourAvg, setPeakHourAvg] = useState<PeakHourAnalytics | null>(null);
  const [weekdayStats, setWeekdayStats] = useState<WeekdayStats[]>([]);
  const [averages, setAverages] = useState<Averages | null>(null);
  const [growthTrend, setGrowthTrend] = useState<GrowthTrend | null>(null);
  const [peakPrediction, setPeakPrediction] = useState<PeakPrediction | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [hasAnyData, setHasAnyData] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [streamMode, setStreamMode] = useState<'local' | 'vps'>('local');
  const analyticsReceivedRef = useRef(false);
  const toast = useToast();

  useEffect(() => {
    streamAPI.getConfig().then((c: { stream_mode?: 'local' | 'vps' }) => setStreamMode(c?.stream_mode || 'local')).catch(() => {});
  }, []);

  const applyAnalyticsSnapshot = (data: Record<string, unknown>) => {
    if (data.current) setCurrentStats(data.current as any);
    if (data.day) setDayStats(data.day as any);
    if (data.week) setWeekStats(data.week as any);
    if (data.month) setMonthStats(data.month as any);
    if (data.hourly) setHourlyStats(data.hourly as any);
    if (data.daily_range) setDailyTrendStats(data.daily_range as any);
    if (data.monthly_range) setMonthlyTrendStats(data.monthly_range as any);
    if (data.peak_hour_avg) setPeakHourAvg(data.peak_hour_avg as any);
    if (data.weekday_stats) setWeekdayStats(data.weekday_stats as any);
    if (data.averages) setAverages(data.averages as any);
    if (data.growth_trend) setGrowthTrend(data.growth_trend as any);
    if (data.predict_peak) setPeakPrediction(data.predict_peak as any);
    const day = data.day as any;
    const week = data.week as any;
    const month = data.month as any;
    const hourly = (data.hourly as any[]) || [];
    const dailyTrend = (data.daily_range as any[]) || [];
    const monthlyTrend = (data.monthly_range as any[]) || [];
    const hasData = (day?.total_events || 0) > 0 ||
      (week?.total_events || 0) > 0 ||
      (month?.total_events || 0) > 0 ||
      hourly.some((h: any) => (h.in_count || 0) > 0 || (h.out_count || 0) > 0) ||
      dailyTrend.some((d: any) => (d.IN || 0) > 0 || (d.OUT || 0) > 0) ||
      monthlyTrend.some((m: any) => (m.IN || 0) > 0 || (m.OUT || 0) > 0);
    setHasAnyData(hasData);
  };

  const fetchData = async (showLoading = true) => {
    try {
      if (showLoading) setIsLoading(true);
      const [current, day, week, month, hourly, dailyTrend, monthlyTrend, peakHour, weekday, avg, trend, prediction] = await Promise.all([
        statsAPI.getCurrent(),
        statsAPI.getDay(),
        statsAPI.getWeek(),
        statsAPI.getMonth(),
        statsAPI.getHourly(),
        statsAPI.getDailyRange(),
        statsAPI.getMonthlyRange(),
        statsAPI.getPeakHourAvg(30),
        statsAPI.getWeekdayStats(30),
        statsAPI.getAverages(),
        statsAPI.getGrowthTrend(),
        statsAPI.getPredictPeak(30),
      ]);
      setCurrentStats(current);
      setDayStats(day);
      setWeekStats(week);
      setMonthStats(month);
      setHourlyStats(hourly);
      setDailyTrendStats(dailyTrend);
      setMonthlyTrendStats(monthlyTrend);
      setPeakHourAvg(peakHour);
      setWeekdayStats(weekday);
      setAverages(avg);
      setGrowthTrend(trend);
      setPeakPrediction(prediction);
      const hasData = (day?.total_events || 0) > 0 ||
        (week?.total_events || 0) > 0 ||
        (month?.total_events || 0) > 0 ||
        hourly.some((h: any) => h.in_count > 0 || h.out_count > 0) ||
        dailyTrend.some((d: any) => (d.IN || d.in_count) > 0 || (d.OUT || d.out_count) > 0) ||
        monthlyTrend.some((m: any) => (m.IN || m.in_count) > 0 || (m.OUT || m.out_count) > 0);
      setHasAnyData(hasData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchData(true);
    toast({
      title: 'Данные обновлены',
      status: 'success',
      duration: 2000,
    });
  };

  // WebSocket: данные аналитики приходят по сокету (при подключении и раз в 30 сек), без опроса REST
  useEffect(() => {
    const base = API_BASE_URL || (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://localhost:8000');
    const wsUrl = (base.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://').replace(/\/$/, '')) + '/ws';
    let ws: WebSocket | null = null;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
    let connectTimeout: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
          if (unmounted) return;
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'analytics' && msg.data) {
              analyticsReceivedRef.current = true;
              if (fallbackTimer) {
                clearTimeout(fallbackTimer);
                fallbackTimer = null;
              }
              applyAnalyticsSnapshot(msg.data);
              setIsLoading(false);
            }
          } catch (_) {}
        };
        ws.onopen = () => {
          if (unmounted) return;
        };
        ws.onerror = () => {};
        ws.onclose = () => {
          ws = null;
          if (fallbackTimer) {
            clearTimeout(fallbackTimer);
            fallbackTimer = null;
          }
          if (!unmounted) setTimeout(connect, 5000);
        };
      } catch (_) {
        if (!unmounted) setIsLoading(false);
      }
    };

    // Fallback: если за 6 сек не пришло данных по WS (сокет не подключился или нет сообщения analytics) — один раз REST
    fallbackTimer = setTimeout(() => {
      fallbackTimer = null;
      if (!unmounted && !analyticsReceivedRef.current) fetchData(false);
    }, 6000);

    // Небольшая задержка, чтобы в React Strict Mode cleanup успел выполниться до открытия сокета
    connectTimeout = setTimeout(connect, 150);

    return () => {
      unmounted = true;
      if (connectTimeout) clearTimeout(connectTimeout);
      if (fallbackTimer) clearTimeout(fallbackTimer);
      if (ws) try { ws.close(); } catch (_) {}
    };
  }, []);

  const handleExport = async (format: 'csv' | 'excel' | 'pdf') => {
    setIsExporting(true);
    try {
      await exportAPI.exportData(format, format === 'pdf');
      toast({
        title: 'Экспорт успешен',
        description: `Файл ${format.toUpperCase()} загружен`,
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Ошибка экспорта',
        description: error.message || 'Не удалось экспортировать данные',
        status: 'error',
        duration: 4000,
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleLogout = () => {
    logout();
    toast({
      title: 'Выход выполнен',
      status: 'info',
      duration: 2000,
    });
  };

  // Format hourly data for charts
  const hourlyChartData = hourlyStats.map(h => ({
    hour: `${h.hour}:00`,
    'Вошло': h.in_count,
    'Вышло': h.out_count,
  }));

  // Format daily trend data for charts
  const dailyTrendChartData = dailyTrendStats.map(d => {
    // Extract day from date (YYYY-MM-DD -> DD)
    const [year, month, day] = d.date.split('-');
    const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    const monthName = monthNames[parseInt(month) - 1];
    return {
      date: parseInt(day).toString(), // Convert "01" to "1"
      fullDate: `${parseInt(day)} ${monthName} ${year}`, // Full date for tooltip
      'Вошло': d.IN,
      'Вышло': d.OUT,
    };
  });

  // Format monthly trend data for charts
  const monthlyTrendChartData = monthlyTrendStats.map(m => {
    // Convert YYYY-MM to Month name
    const [year, month] = m.month.split('-');
    const monthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    const monthName = monthNames[parseInt(month) - 1];
    return {
      month: monthName,
      fullMonth: `${monthName} ${year}`,
      'Вошло': m.IN,
      'Вышло': m.OUT,
    };
  });

  // Chart.js data: weekday bar
  const weekdayChartData = {
    labels: weekdayStats.map(w => w.weekday),
    datasets: [
      { label: 'Вошло', data: weekdayStats.map(w => w.IN), backgroundColor: CHART_COLORS.in, borderColor: CHART_COLORS.in, borderWidth: 1 },
      { label: 'Вышло', data: weekdayStats.map(w => w.OUT), backgroundColor: CHART_COLORS.out, borderColor: CHART_COLORS.out, borderWidth: 1 },
    ],
  };

  // Chart.js data: hourly (bar + line)
  const hourlyChartJsData = {
    labels: hourlyChartData.map(h => h.hour),
    datasets: [
      { label: 'Вошло', data: hourlyChartData.map(h => h['Вошло']), backgroundColor: CHART_COLORS.in, borderColor: CHART_COLORS.in, borderWidth: 2, tension: 0.35, fill: false },
      { label: 'Вышло', data: hourlyChartData.map(h => h['Вышло']), backgroundColor: CHART_COLORS.out, borderColor: CHART_COLORS.out, borderWidth: 2, tension: 0.35, fill: false },
    ],
  };

  // Chart.js data: daily trend line
  const dailyChartJsData = {
    labels: dailyTrendChartData.map(d => d.date),
    datasets: [
      { label: 'Вошло', data: dailyTrendChartData.map(d => d['Вошло']), borderColor: CHART_COLORS.in, backgroundColor: CHART_COLORS.in, borderWidth: 2, tension: 0.35, fill: false, pointRadius: 4, pointHoverRadius: 6 },
      { label: 'Вышло', data: dailyTrendChartData.map(d => d['Вышло']), borderColor: CHART_COLORS.out, backgroundColor: CHART_COLORS.out, borderWidth: 2, tension: 0.35, fill: false, pointRadius: 4, pointHoverRadius: 6 },
    ],
  };

  // Chart.js data: monthly trend line
  const monthlyChartJsData = {
    labels: monthlyTrendChartData.map(m => m.month),
    datasets: [
      { label: 'Вошло', data: monthlyTrendChartData.map(m => m['Вошло']), borderColor: CHART_COLORS.in, backgroundColor: CHART_COLORS.in, borderWidth: 2, tension: 0.35, fill: false, pointRadius: 4, pointHoverRadius: 6 },
      { label: 'Вышло', data: monthlyTrendChartData.map(m => m['Вышло']), borderColor: CHART_COLORS.out, backgroundColor: CHART_COLORS.out, borderWidth: 2, tension: 0.35, fill: false, pointRadius: 4, pointHoverRadius: 6 },
    ],
  };

  const hourlyTooltipTitle = () => {
    const now = new Date();
    const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return `${now.getDate()} ${monthNames[now.getMonth()]} ${now.getFullYear()}`;
  };

  // Empty State для отдельного блока
  const EmptyStateBlock = ({ icon, title, description }: { icon: any, title: string, description: string }) => (
    <Flex 
      direction="column" 
      align="center" 
      justify="center" 
      py={{ base: 6, md: 10 }}
      color="gray.500"
    >
      <Icon as={icon} boxSize={{ base: 10, md: 12 }} mb={3} color="gray.400" />
      <Heading size={{ base: "sm", md: "md" }} mb={2} color="gray.600">{title}</Heading>
      <Text fontSize={{ base: "sm", md: "md" }} textAlign="center">{description}</Text>
    </Flex>
  );

  // Empty State для всей страницы
  const EmptyStatePage = () => (
    <Container maxW="container.xl" py={{ base: 8, md: 16 }}>
      <VStack spacing={6} align="center" justify="center" minH="60vh">
        <Icon as={FaChartLine} boxSize={{ base: 20, md: 24 }} color="gray.300" />
        <VStack spacing={3}>
          <Heading size={{ base: "lg", md: "xl" }} color="gray.600">
            Пока нет данных для аналитики
          </Heading>
          <Text fontSize={{ base: "md", md: "lg" }} color="gray.500" textAlign="center" maxW="600px">
            Аналитические данные появятся после того, как система начнет отслеживать людей.
            Убедитесь, что камера подключена и система работает.
          </Text>
        </VStack>
        <VStack spacing={3} mt={4}>
          <Button
            leftIcon={<FaChartBar />}
            colorScheme="brand"
            size={{ base: "md", md: "lg" }}
            onClick={handleRefresh}
            isLoading={isLoading}
          >
            Обновить данные
          </Button>
          <Button
            as="a"
            href={`${window.location.protocol}//${window.location.hostname}:3000`}
            target="_blank"
            rel="noopener noreferrer"
            variant="link"
            colorScheme="blue"
            textDecoration="underline"
            fontSize={{ base: "sm", md: "md" }}
          >
            Перейти в админ панель
          </Button>
        </VStack>
        <Box bg="blue.50" p={6} borderRadius="lg" mt={8} maxW="600px">
          <HStack spacing={3} align="start">
            <Icon as={FaExclamationCircle} color="blue.500" boxSize={5} mt={1} />
            <VStack align="start" spacing={2}>
              <Text fontWeight="bold" color="blue.900">Как начать собирать данные?</Text>
              <Text fontSize="sm" color="blue.800">
                1. Убедитесь что камера подключена в настройках администратора
              </Text>
              <Text fontSize="sm" color="blue.800">
                2. Проверьте что система распознает людей на видео
              </Text>
              <Text fontSize="sm" color="blue.800">
                3. Данные начнут накапливаться автоматически
              </Text>
            </VStack>
          </HStack>
        </Box>
      </VStack>
    </Container>
  );

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottom="1px" borderColor="gray.200" py={4}>
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center" direction={{ base: "column", md: "row" }} gap={{ base: 3, md: 0 }}>
            <HStack spacing={3}>
              <Heading size={{ base: "md", md: "lg" }}>Аналитическая панель</Heading>
            </HStack>
            <HStack spacing={{ base: 2, md: 4 }}>
              {!isLoading && hasAnyData && (
                <Menu>
                  <MenuButton
                    as={Button}
                    leftIcon={<FaDownload />}
                    rightIcon={<FaChevronDown />}
                    colorScheme="brand"
                    isLoading={isExporting}
                    size={{ base: "sm", md: "md" }}
                  >
                    <Text display={{ base: "none", md: "inline" }}>Экспорт</Text>
                    <Text display={{ base: "inline", md: "none" }}>CSV</Text>
                  </MenuButton>
                  <MenuList>
                    <MenuItem onClick={() => handleExport('csv')}>
                      Экспорт в CSV
                    </MenuItem>
                    <MenuItem onClick={() => handleExport('excel')}>
                      Экспорт в Excel
                    </MenuItem>
                  </MenuList>
                </Menu>
              )}
              <Button
                leftIcon={<FaSignOutAlt />}
                colorScheme="red"
                variant="ghost"
                onClick={handleLogout}
                size={{ base: "sm", md: "md" }}
              >
                <Text display={{ base: "none", md: "inline" }}>Выйти</Text>
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Show loading spinner or EmptyStatePage or Main Content */}
      {isLoading ? (
        <Center minH="60vh">
          <VStack spacing={4}>
            <Spinner size="xl" color="brand.500" thickness="4px" />
            <Text color="gray.600">Загрузка данных...</Text>
          </VStack>
        </Center>
      ) : !hasAnyData ? (
        <EmptyStatePage />
      ) : (
        /* Main Content */
        <Container maxW="container.xl" py={{ base: 4, md: 8 }} px={{ base: 3, md: 4 }}>
        <VStack 
          spacing={{ base: 4, md: 6 }} 
          align="stretch"
          maxH={{ base: "calc(100vh - 180px)", lg: "none" }}
          overflowY={{ base: "auto", lg: "visible" }}
          pr={{ base: 2, lg: 0 }}
        >
          {/* Current Stats Cards */}
          <Grid templateColumns={{ base: "1fr", sm: "repeat(3, 1fr)" }} gap={{ base: 3, md: 4 }}>
            <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel fontSize={{ base: "sm", md: "md" }}>Вошло сегодня</StatLabel>
                <StatNumber fontSize={{ base: "2xl", md: "3xl" }} color="green.500">
                  {dayStats?.in_count || 0}
                </StatNumber>
                <StatHelpText fontSize={{ base: "xs", md: "sm" }}>За текущий день</StatHelpText>
              </Stat>
            </Box>

            <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel fontSize={{ base: "sm", md: "md" }}>Вышло сегодня</StatLabel>
                <StatNumber fontSize={{ base: "2xl", md: "3xl" }} color="red.500">
                  {dayStats?.out_count || 0}
                </StatNumber>
                <StatHelpText fontSize={{ base: "xs", md: "sm" }}>За текущий день</StatHelpText>
              </Stat>
            </Box>

            <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel fontSize={{ base: "sm", md: "md" }}>Активные треки</StatLabel>
                <StatNumber fontSize={{ base: "2xl", md: "3xl" }} color="purple.500">
                  {currentStats?.active_tracks || 0}
                </StatNumber>
                <StatHelpText fontSize={{ base: "xs", md: "sm" }}>Сейчас в кадре</StatHelpText>
              </Stat>
            </Box>
          </Grid>

        {/* Advanced Analytics Section */}
        <Grid templateColumns={{ base: '1fr', lg: 'repeat(3, 1fr)' }} gap={{ base: 3, md: 6 }} mb={{ base: 3, md: 6 }}>
          {/* Average Peak Hour */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Самый пиковый час</Heading>
            {peakHourAvg && peakHourAvg.peak_hour !== null && peakHourAvg.total_count > 0 ? (
              <>
                <Stat>
                  <StatLabel fontSize={{ base: "sm", md: "md" }}>Час пиковой активности</StatLabel>
                  <StatNumber fontSize={{ base: "3xl", md: "4xl" }}>{peakHourAvg.peak_hour}:00</StatNumber>
                  <StatHelpText fontSize={{ base: "xs", md: "sm" }}>
                    Среднее: {peakHourAvg.avg_count.toFixed(1)} посетителей/день
                  </StatHelpText>
                  <StatHelpText fontSize={{ base: "xs", md: "sm" }}>
                    Всего за период: {peakHourAvg.total_count}
                  </StatHelpText>
                </Stat>
              </>
            ) : (
              <EmptyStateBlock 
                icon={FaClock} 
                title="Нет данных о пиковых часах" 
                description="Данные появятся после накопления статистики за несколько дней"
              />
            )}
          </Box>

          {/* Averages */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Средние показатели</Heading>
            {averages && (averages.avg_per_day > 0 || averages.avg_per_week > 0 || averages.avg_per_month > 0) ? (
              <VStack align="stretch" spacing={3}>
                <Stat>
                  <StatLabel fontSize={{ base: "sm", md: "md" }}>За день</StatLabel>
                  <StatNumber fontSize={{ base: "xl", md: "2xl" }}>{averages.avg_per_day.toFixed(1)}</StatNumber>
                  <StatHelpText fontSize={{ base: "xs", md: "sm" }}>посетителей</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel fontSize={{ base: "sm", md: "md" }}>За неделю</StatLabel>
                  <StatNumber fontSize={{ base: "xl", md: "2xl" }}>{averages.avg_per_week.toFixed(1)}</StatNumber>
                  <StatHelpText fontSize={{ base: "xs", md: "sm" }}>посетителей</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel fontSize={{ base: "sm", md: "md" }}>За месяц</StatLabel>
                  <StatNumber fontSize={{ base: "xl", md: "2xl" }}>{averages.avg_per_month.toFixed(1)}</StatNumber>
                  <StatHelpText fontSize={{ base: "xs", md: "sm" }}>посетителей</StatHelpText>
                </Stat>
              </VStack>
            ) : (
              <EmptyStateBlock 
                icon={FaChartLine} 
                title="Нет средних показателей" 
                description="Средние значения будут рассчитаны после сбора данных"
              />
            )}
          </Box>

          {/* Growth Trend */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Тренд роста/падения</Heading>
            {growthTrend && (growthTrend.week_change_percent !== 0 || growthTrend.month_change_percent !== 0) ? (
              <VStack align="stretch" spacing={3}>
                <Stat>
                  <StatLabel>За неделю</StatLabel>
                  <StatNumber color={growthTrend.week_change_percent > 0 ? 'green.500' : growthTrend.week_change_percent < 0 ? 'red.500' : 'gray.500'}>
                    {growthTrend.week_change_percent > 0 ? '+' : ''}{growthTrend.week_change_percent}%
                  </StatNumber>
                  <StatHelpText>
                    {growthTrend.trend === 'up' ? '📈 Рост' : growthTrend.trend === 'down' ? '📉 Падение' : '➡️ Стабильно'}
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>За месяц</StatLabel>
                  <StatNumber color={growthTrend.month_change_percent > 0 ? 'green.500' : growthTrend.month_change_percent < 0 ? 'red.500' : 'gray.500'}>
                    {growthTrend.month_change_percent > 0 ? '+' : ''}{growthTrend.month_change_percent}%
                  </StatNumber>
                  <StatHelpText>по сравнению с прошлым месяцем</StatHelpText>
                </Stat>
              </VStack>
            ) : (
              <EmptyStateBlock 
                icon={FaChartLine} 
                title="Нет данных о тренде" 
                description="Тренды роста/падения будут доступны после накопления исторических данных"
              />
            )}
          </Box>
        </Grid>

        {/* Peak Prediction */}
        <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm" mb={{ base: 3, md: 6 }}>
          <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Предсказание пика на основе истории</Heading>
          {peakPrediction && peakPrediction.predicted_hour !== null && peakPrediction.expected_count > 0 ? (
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }} gap={{ base: 3, md: 6 }}>
              <Stat>
                <StatLabel>Ожидаемый пик</StatLabel>
                <StatNumber fontSize="3xl">{peakPrediction.predicted_hour}:00</StatNumber>
                <StatHelpText>через {peakPrediction.hours_until}ч</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Ожидаемое количество</StatLabel>
                <StatNumber>{peakPrediction.expected_count.toFixed(1)}</StatNumber>
                <StatHelpText>посетителей</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Уверенность</StatLabel>
                <StatNumber>{peakPrediction.confidence.toFixed(1)}%</StatNumber>
                <StatHelpText>на основе истории</StatHelpText>
              </Stat>
              <Box>
                <Text fontSize="sm" color="gray.600" mb={2}>Рекомендация:</Text>
                <Text fontSize="sm" fontWeight="bold">
                  {peakPrediction.hours_until < 2 
                    ? '⚠️ Пик скоро! Будьте готовы' 
                    : peakPrediction.hours_until < 4 
                    ? '🔔 Пик приближается' 
                    : '✅ Достаточно времени'}
                </Text>
              </Box>
            </Grid>
          ) : (
            <EmptyStateBlock 
              icon={FaClock} 
              title="Недостаточно данных для предсказания" 
              description="Предсказания будут доступны после накопления исторических данных за несколько дней"
            />
          )}
        </Box>

        {/* Weekday Statistics */}
        <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm" mb={{ base: 3, md: 6 }}>
          <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Самые активные дни недели</Heading>
          {weekdayStats.length > 0 ? (
            <Box overflowX={{ base: "auto", lg: "visible" }} w="100%">
              <Box minW={{ base: "800px", lg: "100%" }} h={{ base: "250px", md: "300px" }}>
                <Bar data={weekdayChartData} options={barChartOptions} />
              </Box>
            </Box>
          ) : (
            <EmptyStateBlock 
              icon={FaCalendarAlt} 
              title="Нет данных по дням недели" 
              description="Статистика по дням недели появится после накопления данных"
            />
          )}
        </Box>

        {/* Period Statistics */}
        <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>Статистика по периодам</Heading>
            <Tabs colorScheme="brand">
              <TabList>
                <Tab>День</Tab>
                <Tab>Неделя</Tab>
                <Tab>Месяц</Tab>
              </TabList>

              <TabPanels>
                <TabPanel>
                  <Grid templateColumns="repeat(3, 1fr)" gap={4}>
                    <Stat>
                      <StatLabel>Вошло</StatLabel>
                      <StatNumber color="green.500">{dayStats?.in_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Вышло</StatLabel>
                      <StatNumber color="red.500">{dayStats?.out_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Всего событий</StatLabel>
                      <StatNumber>{dayStats?.total_events || 0}</StatNumber>
                    </Stat>
                  </Grid>
                </TabPanel>

                <TabPanel>
                  <Grid templateColumns="repeat(3, 1fr)" gap={4}>
                    <Stat>
                      <StatLabel>Вошло</StatLabel>
                      <StatNumber color="green.500">{weekStats?.in_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Вышло</StatLabel>
                      <StatNumber color="red.500">{weekStats?.out_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Всего событий</StatLabel>
                      <StatNumber>{weekStats?.total_events || 0}</StatNumber>
                    </Stat>
                  </Grid>
                </TabPanel>

                <TabPanel>
                  <Grid templateColumns="repeat(3, 1fr)" gap={4}>
                    <Stat>
                      <StatLabel>Вошло</StatLabel>
                      <StatNumber color="green.500">{monthStats?.in_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Вышло</StatLabel>
                      <StatNumber color="red.500">{monthStats?.out_count || 0}</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Всего событий</StatLabel>
                      <StatNumber>{monthStats?.total_events || 0}</StatNumber>
                    </Stat>
                  </Grid>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Box>

          {/* Live Video */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm" mb={{ base: 3, md: 6 }}>
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Live видео</Heading>
            <Box
              position="relative"
              w="full"
              h={{ base: "250px", md: "400px" }}
              bg="gray.100"
              borderRadius="md"
              overflow="hidden"
            >
              {(streamMode === 'vps' || currentStats?.camera_status === 'online') ? (
                <StreamPlayer apiBaseUrl={API_BASE_URL} />
              ) : (
                <Flex h="full" align="center" justify="center">
                  <Text color="gray.500">Камера отключена</Text>
                </Flex>
              )}
            </Box>
          </Box>

          {/* Hourly Bar Chart */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm" mb={{ base: 3, md: 6 }}>
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Дневная активность</Heading>
            <Box overflowX={{ base: "auto", lg: "visible" }} w="100%">
              <Box minW={{ base: "1200px", lg: "100%" }} h={{ base: "250px", md: "300px" }}>
                <Bar data={hourlyChartJsData} options={barChartOptions} />
              </Box>
            </Box>
          </Box>

          {/* Trend Analysis */}
          <Box bg="white" p={{ base: 4, md: 6 }} borderRadius="lg" boxShadow="sm">
            <Heading size={{ base: "sm", md: "md" }} mb={{ base: 3, md: 4 }}>Тренд</Heading>
            <Tabs colorScheme="brand" size={{ base: "sm", md: "md" }}>
              <TabList>
                <Tab fontSize={{ base: "sm", md: "md" }}>Почасовой</Tab>
                <Tab fontSize={{ base: "sm", md: "md" }}>День</Tab>
                <Tab fontSize={{ base: "sm", md: "md" }}>Месяц</Tab>
              </TabList>

              <TabPanels>
                {/* Hourly Trend */}
                <TabPanel>
                  <Box overflowX={{ base: "auto", lg: "visible" }} w="100%">
                    <Box minW={{ base: "1200px", lg: "100%" }} h={{ base: "250px", md: "300px" }}>
                      <Line data={hourlyChartJsData} options={{ ...lineChartOptions, plugins: { ...lineChartOptions.plugins, tooltip: { ...lineChartOptions.plugins?.tooltip, callbacks: { title: () => hourlyTooltipTitle() } } } }} />
                    </Box>
                  </Box>
                  <Text mt={3} fontSize="sm" color="gray.600" textAlign="center">
                    Анализ активности по часам дня
                  </Text>
                </TabPanel>

                {/* Daily Trend */}
                <TabPanel>
                  <Box overflowX={{ base: "auto", lg: "visible" }} w="100%">
                    <Box minW={{ base: "1400px", lg: "100%" }} h={{ base: "250px", md: "300px" }}>
                      <Line data={dailyChartJsData} options={{ ...lineChartOptions, plugins: { ...lineChartOptions.plugins, tooltip: { ...lineChartOptions.plugins?.tooltip, callbacks: { title: (items) => items.length && items[0].dataIndex != null ? dailyTrendChartData[items[0].dataIndex]?.fullDate ?? '' : '' } } } }} />
                    </Box>
                  </Box>
                  <Text mt={3} fontSize="sm" color="gray.600" textAlign="center">
                    Анализ активности по дням месяца
                  </Text>
                </TabPanel>

                {/* Monthly Trend */}
                <TabPanel>
                  <Box overflowX={{ base: "auto", lg: "visible" }} w="100%">
                    <Box minW={{ base: "1000px", lg: "100%" }} h={{ base: "250px", md: "300px" }}>
                      <Line data={monthlyChartJsData} options={{ ...lineChartOptions, plugins: { ...lineChartOptions.plugins, tooltip: { ...lineChartOptions.plugins?.tooltip, callbacks: { title: (items) => items.length && items[0].dataIndex != null ? monthlyTrendChartData[items[0].dataIndex]?.fullMonth ?? '' : '' } } } }} />
                    </Box>
                  </Box>
                  <Text mt={3} fontSize="sm" color="gray.600" textAlign="center">
                    Анализ активности по месяцам года
                  </Text>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Box>
        </VStack>
      </Container>
      )}
    </Box>
  );
}
