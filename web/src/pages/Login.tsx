import { useState } from 'react';
import {
  Box, Button, Container, FormControl, FormLabel, Heading, Input, InputGroup, InputRightElement, IconButton,
  VStack, Text, Link, useToast, Flex,
} from '@chakra-ui/react';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { t } from '../i18n';

export default function Login() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      toast({
        title: 'Error',
        description: err.response?.data?.detail || 'Something went wrong',
        status: 'error',
        duration: 4000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex minH="100vh" align="center" justify="center" bg="gray.50">
      <Container maxW="sm">
        <Box bg="white" p={8} borderRadius="xl" boxShadow="lg">
          <VStack spacing={6} as="form" onSubmit={handleSubmit}>
            <Heading size="lg" color="gray.800">
              {isRegister ? t('auth.register') : t('auth.login')}
            </Heading>

            {isRegister && (
              <FormControl isRequired>
                <FormLabel>{t('auth.name')}</FormLabel>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('auth.namePlaceholder')} />
              </FormControl>
            )}

            <FormControl isRequired>
              <FormLabel>{t('auth.email')}</FormLabel>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t('auth.emailPlaceholder')} />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>{t('auth.password')}</FormLabel>
              <InputGroup>
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('auth.passwordPlaceholder')}
                />
                <InputRightElement>
                  <IconButton
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    icon={showPassword ? <FiEyeOff /> : <FiEye />}
                    onClick={() => setShowPassword((v) => !v)}
                    variant="ghost"
                    size="sm"
                  />
                </InputRightElement>
              </InputGroup>
            </FormControl>

            <Button type="submit" colorScheme="blue" w="full" isLoading={loading}>
              {isRegister ? t('auth.register') : t('auth.login')}
            </Button>

            <Text fontSize="sm" color="gray.600">
              {isRegister ? t('auth.hasAccount') : t('auth.noAccount')}{' '}
              <Link color="blue.500" onClick={() => setIsRegister(!isRegister)}>
                {isRegister ? t('auth.login') : t('auth.register')}
              </Link>
            </Text>
          </VStack>
        </Box>
      </Container>
    </Flex>
  );
}
