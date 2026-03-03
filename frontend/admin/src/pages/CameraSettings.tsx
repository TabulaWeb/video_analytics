import { useState, useEffect } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  FormHelperText,
  Heading,
  Input,
  InputGroup,
  InputRightElement,
  IconButton,
  VStack,
  HStack,
  Select,
  NumberInput,
  NumberInputField,
  useToast,
  Flex,
  Text,
  Divider,
  Badge,
} from '@chakra-ui/react';
import { FaArrowLeft, FaSave, FaEye, FaEyeSlash } from 'react-icons/fa';
import { cameraAPI } from '../services/api';

interface CameraSettings {
  id?: number;
  ip: string;
  port: number;
  username: string;
  password: string;
  channel: number;
  subtype: number;
  line_x: number | null;
  direction_in: 'L->R' | 'R->L';
  hysteresis_px: number;
}

export default function CameraSettings() {
  const [settings, setSettings] = useState<CameraSettings>({
    ip: '192.168.0.201',
    port: 554,
    username: 'admin',
    password: '',
    channel: 1,
    subtype: 0,
    line_x: null,
    direction_in: 'L->R',
    hysteresis_px: 5,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const fetchSettings = async () => {
      setIsLoading(true);
      try {
        const data = await cameraAPI.getSettings();
        // Set defaults for fields not returned from server
        setSettings({
          ...data,
          password: '', // Password is not returned from server for security
          hysteresis_px: data.hysteresis_px ?? 5,
        });
      } catch (error) {
        console.log('No existing settings, using defaults');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleSave = async () => {
    // Validate required fields
    if (!settings.ip || !settings.ip.trim()) {
      toast({
        title: 'Ошибка валидации',
        description: 'IP адрес обязателен',
        status: 'error',
        duration: 4000,
      });
      return;
    }

    if (!settings.username || !settings.username.trim()) {
      toast({
        title: 'Ошибка валидации',
        description: 'Имя пользователя обязательно',
        status: 'error',
        duration: 4000,
      });
      return;
    }

    // Validate password only for new settings
    if (!settings.id && !settings.password) {
      toast({
        title: 'Ошибка валидации',
        description: 'Пароль обязателен для новых настроек камеры',
        status: 'error',
        duration: 4000,
      });
      return;
    }
    
    // For existing settings, empty password means "don't change"

    if (settings.port < 1 || settings.port > 65535) {
      toast({
        title: 'Ошибка валидации',
        description: 'Порт должен быть от 1 до 65535',
        status: 'error',
        duration: 4000,
      });
      return;
    }

    setIsSaving(true);
    try {
      const result = settings.id
        ? await cameraAPI.updateSettings(settings.id, settings)
        : await cameraAPI.createSettings(settings);
      const connected = (result as { camera_connected?: boolean }).camera_connected !== false;
      const msg = (result as { message?: string }).message;

      if (connected) {
        toast({
          title: 'Настройки сохранены ✅',
          description: 'Камера успешно подключена и перезапущена',
          status: 'success',
          duration: 5000,
        });
      } else {
        toast({
          title: 'Настройки сохранены',
          description: msg || 'Камера пока недоступна с этого сервера. Проверьте сеть или MediaMTX.',
          status: 'warning',
          duration: 8000,
          isClosable: true,
        });
      }
    } catch (error: any) {
      console.error('Save error:', error);
      const status = error.response?.status;
      const errorMessage = error.response?.data?.detail || error.message || 'Не удалось сохранить настройки';
      
      if (status === 503) {
        toast({
          title: '⚠️ Ошибка подключения к камере',
          description: errorMessage,
          status: 'warning',
          duration: 8000,
          isClosable: true,
        });
      } else if (Array.isArray(error.response?.data?.detail)) {
        // Validation errors from FastAPI
        const validationErrors = error.response.data.detail.map((err: any) => 
          `${err.loc?.join('.')}: ${err.msg}`
        ).join(', ');
        
        toast({
          title: 'Ошибка валидации',
          description: validationErrors,
          status: 'error',
          duration: 6000,
          isClosable: true,
        });
      } else {
        // Generic error
        toast({
          title: 'Ошибка сохранения',
          description: errorMessage,
          status: 'error',
          duration: 6000,
          isClosable: true,
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottom="1px" borderColor="gray.200" py={4}>
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center">
            <HStack spacing={3}>
              <Button
                as={RouterLink}
                to="/"
                leftIcon={<FaArrowLeft />}
                variant="ghost"
              >
                Назад
              </Button>
              <Heading size="lg">Настройки камеры</Heading>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Main Content */}
      <Container maxW="container.md" py={8}>
        <Box bg="white" p={8} borderRadius="lg" boxShadow="sm">
          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="md" mb={4}>Параметры IP камеры</Heading>
              <Text color="gray.600" mb={4}>
                Настройте параметры подключения к Dahua IP камере
              </Text>
            </Box>

            <FormControl isRequired>
              <FormLabel>
                IP адрес камеры
                <Badge ml={2} colorScheme="red" fontSize="xs">Обязательно</Badge>
              </FormLabel>
              <Input
                value={settings.ip}
                onChange={(e) => setSettings({ ...settings, ip: e.target.value })}
                placeholder="192.168.0.201"
              />
              <FormHelperText>
                IP адрес вашей камеры (например: 192.168.0.201 или localhost для MediaMTX)
              </FormHelperText>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Порт RTSP</FormLabel>
              <NumberInput
                value={settings.port}
                onChange={(value) => setSettings({ ...settings, port: parseInt(value) })}
                min={1}
                max={65535}
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>
                Имя пользователя
                <Badge ml={2} colorScheme="red" fontSize="xs">Обязательно</Badge>
              </FormLabel>
              <Input
                value={settings.username}
                onChange={(e) => setSettings({ ...settings, username: e.target.value })}
                placeholder="admin"
              />
            </FormControl>

            <FormControl isRequired={!settings.id}>
              <FormLabel>
                Пароль
                {!settings.id && <Badge ml={2} colorScheme="red" fontSize="xs">Обязательно</Badge>}
                {settings.id && <Badge ml={2} colorScheme="gray" fontSize="xs">Необязательно</Badge>}
              </FormLabel>
              <InputGroup>
                <Input
                  type={showPassword ? "text" : "password"}
                  value={settings.password}
                  onChange={(e) => setSettings({ ...settings, password: e.target.value })}
                  placeholder={settings.id ? "••••••••  (оставьте пустым, чтобы не менять)" : "Введите пароль"}
                  pr="4.5rem"
                />
                <InputRightElement width="4.5rem">
                  <IconButton
                    h="1.75rem"
                    size="sm"
                    onClick={() => setShowPassword(!showPassword)}
                    icon={showPassword ? <FaEyeSlash /> : <FaEye />}
                    aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                    variant="ghost"
                  />
                </InputRightElement>
              </InputGroup>
              <FormHelperText color={settings.id ? "blue.600" : "gray.600"}>
                {settings.id 
                  ? "💡 Текущий пароль сохранен. Оставьте поле пустым, если не хотите менять его" 
                  : "Пароль для подключения к камере"}
              </FormHelperText>
            </FormControl>

            <HStack spacing={4}>
              <FormControl>
                <FormLabel>Канал</FormLabel>
                <NumberInput
                  value={settings.channel}
                  onChange={(value) => setSettings({ ...settings, channel: parseInt(value) })}
                  min={1}
                  max={16}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel>Подтип потока</FormLabel>
                <Select
                  value={settings.subtype}
                  onChange={(e) => setSettings({ ...settings, subtype: parseInt(e.target.value) })}
                >
                  <option value={0}>0 - Основной поток (HD)</option>
                  <option value={1}>1 - Дополнительный поток (SD)</option>
                </Select>
              </FormControl>
            </HStack>

            <Divider />

            <Box>
              <Heading size="md" mb={4}>Настройки линии подсчёта</Heading>
              <Text color="gray.600" mb={4}>
                Линия пересечения и направление входа/выхода. Применяется к локальной камере и к анализу VPS.
              </Text>
            </Box>

            <FormControl>
              <FormLabel>Позиция линии (X, пиксели)</FormLabel>
              <NumberInput
                value={settings.line_x ?? ''}
                onChange={(_, valueAsNumber) => setSettings({ ...settings, line_x: Number.isNaN(valueAsNumber) ? null : valueAsNumber })}
                min={0}
                max={1920}
              >
                <NumberInputField placeholder="Авто (центр кадра)" />
              </NumberInput>
              <FormHelperText>
                Горизонтальная координата вертикальной линии. Пусто = центр кадра. Если подсчёт не срабатывает — поставьте линию там, где вы переходите (например 800, если человек всё время справа в кадре). Ширина кадра обычно 960.
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>Дальность срабатывания (пиксели)</FormLabel>
              <NumberInput
                value={settings.hysteresis_px}
                onChange={(_, valueAsNumber) => setSettings({ ...settings, hysteresis_px: Number.isNaN(valueAsNumber) ? 5 : Math.max(1, Math.min(100, valueAsNumber)) })}
                min={1}
                max={100}
              >
                <NumberInputField />
              </NumberInput>
              <FormHelperText>
                Насколько далеко за линию должен перейти центр человека, чтобы пересечение засчиталось. Больше = меньше ложных срабатываний, меньше = чувствительнее.
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>Направление входа</FormLabel>
              <Select
                value={settings.direction_in}
                onChange={(e) => setSettings({ ...settings, direction_in: e.target.value as 'L->R' | 'R->L' })}
              >
                <option value="L->R">Слева направо (L→R) = вход</option>
                <option value="R->L">Справа налево (R→L) = вход</option>
              </Select>
              <FormHelperText>
                Какое направление пересечения считать «входом». Если считает только выход при вашем входе — выберите «Справа налево».
              </FormHelperText>
            </FormControl>

            <Button
              leftIcon={<FaSave />}
              colorScheme="brand"
              size="lg"
              onClick={handleSave}
              isLoading={isSaving}
              loadingText="Сохранение..."
            >
              Сохранить настройки
            </Button>
          </VStack>
        </Box>
      </Container>
    </Box>
  );
}
