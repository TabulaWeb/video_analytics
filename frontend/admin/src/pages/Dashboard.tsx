import { useEffect, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
  Badge,
  useToast,
  Icon,
  Flex,
} from '@chakra-ui/react';
import { FaCog, FaSignOutAlt, FaCircle, FaChartBar } from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { systemAPI } from '../services/api';
import StreamPlayer from '../components/StreamPlayer';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface SystemStatus {
  camera_online: boolean;
  fps: number;
  active_tracks: number;
  model_loaded: boolean;
  uptime_seconds: number;
  stream_mode?: 'local' | 'vps';
  vps_status?: 'connecting' | 'live' | 'offline';
}

interface Stats {
  in_count: number;
  out_count: number;
  active_tracks: number;
  camera_status: string;
  model_loaded: boolean;
  fps: number;
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [overlay, setOverlay] = useState<{ frame_width: number; frame_height: number; line_x: number; direction_in: string; boxes: number[][] } | null>(null);
  const toast = useToast();

  const dashboardReceivedRef = useRef(false);

  // Fallback: один раз REST, если по WebSocket не пришёл dashboard
  const fetchDataFallback = async () => {
    try {
      const [statusData, statsData] = await Promise.all([
        systemAPI.getStatus(),
        systemAPI.getCurrentStats(),
      ]);
      setSystemStatus(statusData);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  // WebSocket: dashboard (system_status + stats) приходит при подключении и каждые ~5 сек
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
            if (msg.type === 'dashboard' && msg.data) {
              dashboardReceivedRef.current = true;
              if (fallbackTimer) {
                clearTimeout(fallbackTimer);
                fallbackTimer = null;
              }
              setSystemStatus(msg.data.system_status ?? null);
              setStats(msg.data.stats ?? null);
            }
            if (msg.type === 'overlay' && msg.data && msg.data.frame_width != null) {
              setOverlay(msg.data);
            }
          } catch (_) {}
        };
        ws.onerror = () => {};
        ws.onclose = () => {
          if (!unmounted) setTimeout(connect, 5000);
        };
      } catch (_) {}
    };

    connectTimeout = setTimeout(connect, 150);

    fallbackTimer = setTimeout(() => {
      if (!unmounted && !dashboardReceivedRef.current) fetchDataFallback();
    }, 8000);

    return () => {
      unmounted = true;
      if (connectTimeout) clearTimeout(connectTimeout);
      if (fallbackTimer) clearTimeout(fallbackTimer);
      if (ws) ws.close();
    };
  }, []);

  const handleLogout = () => {
    logout();
    toast({
      title: 'Выход выполнен',
      status: 'info',
      duration: 2000,
    });
  };

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottom="1px" borderColor="gray.200" py={4}>
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center">
            <HStack spacing={3}>
              <Heading size="lg">Админ Панель</Heading>
            </HStack>
            <HStack spacing={4}>
              <Button
                leftIcon={<FaChartBar />}
                colorScheme="blue"
                variant="ghost"
                onClick={() => {
                  const token = localStorage.getItem('token');
                  window.open(`http://localhost:3002/?token=${token}`, '_blank');
                }}
              >
                Открыть аналитику
              </Button>
              <Button
                as={RouterLink}
                to="/camera"
                leftIcon={<FaCog />}
                colorScheme="gray"
                variant="ghost"
              >
                Настройки камеры
              </Button>
              <Button
                leftIcon={<FaSignOutAlt />}
                colorScheme="red"
                variant="ghost"
                onClick={handleLogout}
              >
                Выйти
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Main Content */}
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* System Status */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Статус системы</Heading>
            <Grid templateColumns="repeat(4, 1fr)" gap={4}>
              <Stat>
                <StatLabel>Камера</StatLabel>
                <HStack>
                  <Icon
                    as={FaCircle}
                    boxSize={3}
                    color={systemStatus?.camera_online ? 'green.500' : 'red.500'}
                  />
                  <StatNumber fontSize="lg">
                    {systemStatus?.camera_online ? 'Онлайн' : 'Оффлайн'}
                  </StatNumber>
                </HStack>
              </Stat>

              <Stat>
                <StatLabel>FPS</StatLabel>
                <StatNumber>{systemStatus?.fps.toFixed(1) || '0.0'}</StatNumber>
              </Stat>

              <Stat>
                <StatLabel>Активные треки</StatLabel>
                <StatNumber>{systemStatus?.active_tracks || 0}</StatNumber>
              </Stat>

              <Stat>
                <StatLabel>Модель</StatLabel>
                <HStack>
                  <Badge colorScheme={systemStatus?.model_loaded ? 'green' : 'red'}>
                    {systemStatus?.model_loaded ? 'Загружена' : 'Не загружена'}
                  </Badge>
                </HStack>
              </Stat>
            </Grid>
          </Box>

          {/* Live Video */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Live видео</Heading>
            <Box
              position="relative"
              w="full"
              h="500px"
              bg="gray.100"
              borderRadius="md"
              overflow="hidden"
            >
              {(systemStatus?.stream_mode === 'vps' || systemStatus?.camera_online) ? (
                <StreamPlayer apiBaseUrl={API_BASE_URL} overlay={overlay} />
              ) : (
                <Flex h="full" align="center" justify="center" flexDirection="column" gap={4}>
                  <Text color="gray.500" fontSize="xl">📹 Камера отключена</Text>
                  <Text color="gray.400" fontSize="sm">Настройте камеру в разделе &quot;Настройки камеры&quot;</Text>
                </Flex>
              )}
            </Box>
          </Box>

          {/* Quick Actions */}
          <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
            <Heading size="md" mb={4}>Быстрые действия</Heading>
            <HStack spacing={4}>
              <Button as={RouterLink} to="/camera" colorScheme="brand" leftIcon={<FaCog />}>
                Настроить камеру
              </Button>
              <Button
                colorScheme="blue"
                onClick={() => window.open(`${window.location.protocol}//${window.location.hostname}:3001`, '_blank')}
              >
                Открыть аналитику
              </Button>
            </HStack>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
}
