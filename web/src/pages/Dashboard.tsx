import { useEffect, useMemo, useState } from 'react';
import {
  Box, Container, Flex, Grid, Heading, HStack, Select, Stat, StatLabel,
  StatNumber, StatHelpText, VStack, Text, Button, Tabs, TabList, Tab,
  TabPanels, TabPanel, Spinner, Center, Icon, Menu, MenuButton, MenuList,
  MenuItem, useToast,
} from '@chakra-ui/react';
import { Chart } from 'react-charts';
import {
  FaSignOutAlt, FaDownload, FaChevronDown, FaChartLine,
  FaClock, FaCalendarAlt, FaExclamationCircle,
} from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { useAnalytics } from '../hooks/useAnalytics';
import { camerasAPI } from '../services/api';
import { t } from '../i18n';
import type { Camera } from '../types';

type Series = { label: string; data: { primary: string; secondary: number }[] };

export default function Dashboard() {
  const { logout } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | undefined>();
  const toast = useToast();

  const {
    day, week, month, hourly, daily, monthly,
    weekdayStats, averages, growthTrend, peakPrediction, peakHourAvg,
    loading, hasData, refresh,
  } = useAnalytics(selectedCamera);

  useEffect(() => {
    camerasAPI.list().then(setCameras).catch(() => {});
  }, []);

  const [activeTab, setActiveTab] = useState(0);
  const periodData = activeTab === 0 ? day : activeTab === 1 ? week : month;

  // ── Chart data for TanStack React Charts ──

  const hourlyChartData: Series[] = useMemo(
    () => [
      {
        label: t('chart.in'),
        data: hourly.map((h) => ({ primary: `${h.hour}:00`, secondary: h.in_count })),
      },
      {
        label: t('chart.out'),
        data: hourly.map((h) => ({ primary: `${h.hour}:00`, secondary: h.out_count })),
      },
    ],
    [hourly],
  );

  const dailyChartData: Series[] = useMemo(
    () => [
      {
        label: t('chart.in'),
        data: daily.map((d) => ({ primary: d.date.slice(5), secondary: d.IN })),
      },
      {
        label: t('chart.out'),
        data: daily.map((d) => ({ primary: d.date.slice(5), secondary: d.OUT })),
      },
    ],
    [daily],
  );

  const monthlyChartData: Series[] = useMemo(
    () => [
      {
        label: t('chart.in'),
        data: monthly.map((m) => ({ primary: m.month, secondary: m.IN })),
      },
      {
        label: t('chart.out'),
        data: monthly.map((m) => ({ primary: m.month, secondary: m.OUT })),
      },
    ],
    [monthly],
  );

  const weekdayChartData: Series[] = useMemo(
    () => [
      {
        label: t('chart.in'),
        data: weekdayStats.map((w) => ({ primary: w.weekday, secondary: w.IN })),
      },
      {
        label: t('chart.out'),
        data: weekdayStats.map((w) => ({ primary: w.weekday, secondary: w.OUT })),
      },
    ],
    [weekdayStats],
  );

  const primaryAxis = useMemo(
    () => ({ getValue: (d: { primary: string }) => d.primary, scaleType: 'band' as const }),
    [],
  );
  const secondaryAxes = useMemo(
    () => [{ getValue: (d: { secondary: number }) => d.secondary, elementType: 'bar' as const, scaleType: 'linear' as const }],
    [],
  );
  const lineSecondaryAxes = useMemo(
    () => [{ getValue: (d: { secondary: number }) => d.secondary, elementType: 'line' as const, scaleType: 'linear' as const }],
    [],
  );

  const hasHourly = hourly.length > 0;
  const hasDaily = daily.length > 0;
  const hasMonthly = monthly.length > 0;
  const hasWeekday = weekdayStats.length > 0;

  // ── Render ──

  if (loading) {
    return (
      <Center minH="80vh">
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" thickness="4px" />
          <Text color="gray.600">{t('loading')}</Text>
        </VStack>
      </Center>
    );
  }

  if (!hasData) {
    return (
      <Container maxW="container.xl" py={16}>
        <VStack spacing={6} align="center" minH="60vh" justify="center">
          <Icon as={FaChartLine} boxSize={24} color="gray.300" />
          <Heading size="xl" color="gray.600">{t('empty.noData')}</Heading>
          <Text fontSize="lg" color="gray.500" textAlign="center" maxW="600px">
            {t('empty.description')}
          </Text>
          <Button colorScheme="blue" size="lg" onClick={refresh}>{t('empty.refresh')}</Button>
        </VStack>
      </Container>
    );
  }

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottom="1px" borderColor="gray.200" py={4} position="sticky" top={0} zIndex={10}>
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center" wrap="wrap" gap={3}>
            <Heading size="lg">{t('app.title')}</Heading>
            <HStack spacing={3} wrap="wrap">
              <Select
                w="200px"
                size="sm"
                value={selectedCamera || ''}
                onChange={(e) => setSelectedCamera(e.target.value || undefined)}
              >
                <option value="">{t('camera.all')}</option>
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </Select>
              <Menu>
                <MenuButton as={Button} size="sm" leftIcon={<FaDownload />} rightIcon={<FaChevronDown />}>
                  {t('export.title')}
                </MenuButton>
                <MenuList>
                  <MenuItem onClick={() => toast({ title: 'CSV export', status: 'info', duration: 2000 })}>
                    {t('export.csv')}
                  </MenuItem>
                  <MenuItem onClick={() => toast({ title: 'Excel export', status: 'info', duration: 2000 })}>
                    {t('export.excel')}
                  </MenuItem>
                </MenuList>
              </Menu>
              <Button size="sm" variant="ghost" colorScheme="red" leftIcon={<FaSignOutAlt />} onClick={logout}>
                {t('nav.logout')}
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      <Container maxW="container.xl" py={6}>
        <VStack spacing={6} align="stretch">
          {/* KPI Cards */}
          <Grid templateColumns={{ base: '1fr', sm: 'repeat(3, 1fr)' }} gap={4}>
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel>{t('stats.inToday')}</StatLabel>
                <StatNumber fontSize="3xl" color="green.500">{day?.in_count ?? 0}</StatNumber>
                <StatHelpText>{t('stats.forToday')}</StatHelpText>
              </Stat>
            </Box>
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel>{t('stats.outToday')}</StatLabel>
                <StatNumber fontSize="3xl" color="red.500">{day?.out_count ?? 0}</StatNumber>
                <StatHelpText>{t('stats.forToday')}</StatHelpText>
              </Stat>
            </Box>
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Stat>
                <StatLabel>{t('stats.activeTracks')}</StatLabel>
                <StatNumber fontSize="3xl" color="purple.500">{day?.net_flow ?? 0}</StatNumber>
                <StatHelpText>{t('stats.inFrame')}</StatHelpText>
              </Stat>
            </Box>
          </Grid>

          {/* Advanced Analytics */}
          <Grid templateColumns={{ base: '1fr', lg: 'repeat(3, 1fr)' }} gap={6}>
            {/* Peak Hour */}
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Heading size="md" mb={4}>{t('stats.peakHour')}</Heading>
              {peakHourAvg && peakHourAvg.peak_hour !== null ? (
                <Stat>
                  <StatLabel>{t('stats.peakActivity')}</StatLabel>
                  <StatNumber fontSize="4xl">{peakHourAvg.peak_hour}:00</StatNumber>
                  <StatHelpText>{peakHourAvg.avg_count.toFixed(1)} {t('stats.avgVisitors')}</StatHelpText>
                  <StatHelpText>{t('stats.totalInPeriod')}: {peakHourAvg.total_count}</StatHelpText>
                </Stat>
              ) : (
                <Flex direction="column" align="center" py={8} color="gray.400">
                  <Icon as={FaClock} boxSize={10} mb={2} />
                  <Text>No data</Text>
                </Flex>
              )}
            </Box>

            {/* Averages */}
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Heading size="md" mb={4}>{t('stats.averages')}</Heading>
              {averages ? (
                <VStack align="stretch" spacing={3}>
                  <Stat><StatLabel>{t('stats.perDay')}</StatLabel><StatNumber>{averages.avg_per_day.toFixed(1)}</StatNumber><StatHelpText>{t('stats.visitors')}</StatHelpText></Stat>
                  <Stat><StatLabel>{t('stats.perWeek')}</StatLabel><StatNumber>{averages.avg_per_week.toFixed(1)}</StatNumber><StatHelpText>{t('stats.visitors')}</StatHelpText></Stat>
                  <Stat><StatLabel>{t('stats.perMonth')}</StatLabel><StatNumber>{averages.avg_per_month.toFixed(1)}</StatNumber><StatHelpText>{t('stats.visitors')}</StatHelpText></Stat>
                </VStack>
              ) : null}
            </Box>

            {/* Growth Trend */}
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Heading size="md" mb={4}>{t('stats.growthTrend')}</Heading>
              {growthTrend ? (
                <VStack align="stretch" spacing={3}>
                  <Stat>
                    <StatLabel>{t('stats.weekChange')}</StatLabel>
                    <StatNumber color={growthTrend.week_change_percent > 0 ? 'green.500' : growthTrend.week_change_percent < 0 ? 'red.500' : 'gray.500'}>
                      {growthTrend.week_change_percent > 0 ? '+' : ''}{growthTrend.week_change_percent}%
                    </StatNumber>
                    <StatHelpText>
                      {growthTrend.trend === 'up' ? t('stats.trendUp') : growthTrend.trend === 'down' ? t('stats.trendDown') : t('stats.trendStable')}
                    </StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>{t('stats.monthChange')}</StatLabel>
                    <StatNumber color={growthTrend.month_change_percent > 0 ? 'green.500' : growthTrend.month_change_percent < 0 ? 'red.500' : 'gray.500'}>
                      {growthTrend.month_change_percent > 0 ? '+' : ''}{growthTrend.month_change_percent}%
                    </StatNumber>
                    <StatHelpText>{t('stats.vsLastMonth')}</StatHelpText>
                  </Stat>
                </VStack>
              ) : null}
            </Box>
          </Grid>

          {/* Peak Prediction */}
          {peakPrediction && peakPrediction.predicted_hour !== null && (
            <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
              <Heading size="md" mb={4}>{t('stats.prediction')}</Heading>
              <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap={4}>
                <Stat>
                  <StatLabel>{t('stats.expectedPeak')}</StatLabel>
                  <StatNumber fontSize="3xl">{peakPrediction.predicted_hour}:00</StatNumber>
                  <StatHelpText>{t('stats.inHours', peakPrediction.hours_until)}</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>{t('stats.expectedCount')}</StatLabel>
                  <StatNumber>{peakPrediction.expected_count.toFixed(1)}</StatNumber>
                  <StatHelpText>{t('stats.visitors')}</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>{t('stats.confidence')}</StatLabel>
                  <StatNumber>{peakPrediction.confidence.toFixed(1)}%</StatNumber>
                  <StatHelpText>{t('stats.basedOnHistory')}</StatHelpText>
                </Stat>
                <Box>
                  <Text fontSize="sm" color="gray.600" mb={2}>{t('stats.recommendation')}:</Text>
                  <Text fontSize="sm" fontWeight="bold">
                    {peakPrediction.hours_until < 2
                      ? t('stats.peakSoon')
                      : peakPrediction.hours_until < 4
                        ? t('stats.peakApproaching')
                        : t('stats.enoughTime')}
                  </Text>
                </Box>
              </Grid>
            </Box>
          )}

          {/* Weekday Chart */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>{t('chart.weekdayActivity')}</Heading>
            {hasWeekday ? (
              <Box h="300px">
                <Chart
                  options={{
                    data: weekdayChartData,
                    primaryAxis,
                    secondaryAxes,
                  }}
                />
              </Box>
            ) : (
              <Flex justify="center" py={8} color="gray.400">
                <Icon as={FaCalendarAlt} boxSize={10} />
              </Flex>
            )}
          </Box>

          {/* Hourly Activity */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>{t('chart.dailyActivity')}</Heading>
            {hasHourly ? (
              <Box h="300px">
                <Chart
                  options={{
                    data: hourlyChartData,
                    primaryAxis,
                    secondaryAxes,
                  }}
                />
              </Box>
            ) : (
              <Flex justify="center" py={8} color="gray.400">
                <Icon as={FaExclamationCircle} boxSize={10} />
              </Flex>
            )}
          </Box>

          {/* Trend Tabs */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>{t('chart.trend')}</Heading>
            <Tabs>
              <TabList>
                <Tab>{t('chart.hourly')}</Tab>
                <Tab>{t('chart.daily')}</Tab>
                <Tab>{t('chart.monthly')}</Tab>
              </TabList>
              <TabPanels>
                <TabPanel>
                  {hasHourly ? (
                    <Box h="300px">
                      <Chart options={{ data: hourlyChartData, primaryAxis, secondaryAxes: lineSecondaryAxes }} />
                    </Box>
                  ) : (
                    <Flex justify="center" py={8} color="gray.400"><Text>{t('empty.noData')}</Text></Flex>
                  )}
                </TabPanel>
                <TabPanel>
                  {hasDaily ? (
                    <Box h="300px">
                      <Chart options={{ data: dailyChartData, primaryAxis, secondaryAxes: lineSecondaryAxes }} />
                    </Box>
                  ) : (
                    <Flex justify="center" py={8} color="gray.400"><Text>{t('empty.noData')}</Text></Flex>
                  )}
                </TabPanel>
                <TabPanel>
                  {hasMonthly ? (
                    <Box h="300px">
                      <Chart options={{ data: monthlyChartData, primaryAxis, secondaryAxes: lineSecondaryAxes }} />
                    </Box>
                  ) : (
                    <Flex justify="center" py={8} color="gray.400"><Text>{t('empty.noData')}</Text></Flex>
                  )}
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Box>

          {/* Period Statistics */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>{t('period.stats')}</Heading>
            <Tabs index={activeTab} onChange={setActiveTab}>
              <TabList>
                <Tab>{t('period.day')}</Tab>
                <Tab>{t('period.week')}</Tab>
                <Tab>{t('period.month')}</Tab>
              </TabList>
              <TabPanels>
                {[0, 1, 2].map((i) => (
                  <TabPanel key={i}>
                    <Grid templateColumns="repeat(3, 1fr)" gap={4}>
                      <Stat>
                        <StatLabel>{t('period.entered')}</StatLabel>
                        <StatNumber color="green.500">{periodData?.in_count ?? 0}</StatNumber>
                      </Stat>
                      <Stat>
                        <StatLabel>{t('period.exited')}</StatLabel>
                        <StatNumber color="red.500">{periodData?.out_count ?? 0}</StatNumber>
                      </Stat>
                      <Stat>
                        <StatLabel>{t('period.totalEvents')}</StatLabel>
                        <StatNumber>{periodData?.total_events ?? 0}</StatNumber>
                      </Stat>
                    </Grid>
                  </TabPanel>
                ))}
              </TabPanels>
            </Tabs>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
}
