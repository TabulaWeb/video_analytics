import { useEffect, useRef, useState } from 'react';
import { Box, Flex, Text, Spinner } from '@chakra-ui/react';
import Hls from 'hls.js';
import { streamAPI } from '../services/api';

export interface StreamConfigType {
  stream_mode: 'local' | 'vps';
  preferred_protocol?: 'webrtc' | 'hls';
  video_feed_url?: string | null;
  vps_hls_url?: string | null;
  vps_webrtc_url?: string | null;
}

export interface VpsStatusType {
  status: 'connecting' | 'live' | 'offline';
  hls_ok?: boolean;
  webrtc_ok?: boolean;
}

const BACKOFF_INITIAL = 2000;   // при подключении / offline
const BACKOFF_MAX = 30000;
const LIVE_POLL_INTERVAL = 15000; // когда уже live — реже, чтобы не дёргать /api/stream/vps-status

function useStreamConfig() {
  const [config, setConfig] = useState<StreamConfigType | null>(null);
  useEffect(() => {
    streamAPI.getConfig().then(setConfig).catch(() => setConfig(null));
  }, []);
  return config;
}

function useVpsStatus(streamMode: 'local' | 'vps', enabled: boolean) {
  const [status, setStatus] = useState<VpsStatusType | null>(null);
  const backoffRef = useRef(BACKOFF_INITIAL);
  useEffect(() => {
    if (streamMode !== 'vps' || !enabled) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const s = await streamAPI.getVpsStatus();
        if (cancelled) return;
        setStatus(s);
        if (s.status === 'live') backoffRef.current = LIVE_POLL_INTERVAL;
        else backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX);
      } catch {
        if (cancelled) return;
        setStatus({ status: 'offline' });
        backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX);
      }
      if (!cancelled) setTimeout(poll, backoffRef.current);
    };
    poll();
    return () => { cancelled = true; };
  }, [streamMode, enabled]);
  return status;
}

function VpsPlayer({
  config,
  vpsStatus,
  videoFeedUrl,
}: {
  config: StreamConfigType;
  vpsStatus: VpsStatusType | null;
  videoFeedUrl: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const preferred = config.preferred_protocol || 'webrtc';
  const [useHls, setUseHls] = useState(preferred === 'hls');
  const [webrtcError, setWebrtcError] = useState(false);
  const hlsRef = useRef<Hls | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const webrtcUrl = (config.vps_webrtc_url || '').trim();
  const hlsUrl = (config.vps_hls_url || '').trim();
  const tryWebrtcFirst = preferred === 'webrtc' && webrtcUrl && !webrtcError;

  // WebRTC WHEP: client sends SDP offer (recvonly) via POST, server responds with 201 + SDP answer
  useEffect(() => {
    if (!tryWebrtcFirst || !videoRef.current || !webrtcUrl) return;
    const whepUrl = webrtcUrl.endsWith('/whep') ? webrtcUrl : webrtcUrl.replace(/\/?$/, '') + '/whep';
    let cancelled = false;
    (async () => {
      try {
        const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        pcRef.current = pc;
        pc.ontrack = (e) => {
          if (videoRef.current && e.streams[0]) videoRef.current.srcObject = e.streams[0];
        };
        // WHEP viewer: offer must be recvonly (spec). Add transceivers before createOffer.
        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        const postRes = await fetch(whepUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: pc.localDescription?.sdp,
        });
        if (!postRes.ok || cancelled) throw new Error(`WHEP failed: ${postRes.status}`);
        const answerSdp = await postRes.text();
        await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      } catch (e) {
        if (!cancelled) setWebrtcError(true);
      }
    })();
    return () => {
      cancelled = true;
      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
    };
  }, [tryWebrtcFirst, webrtcUrl]);

  // HLS fallback (when WebRTC failed or preferred is hls)
  useEffect(() => {
    if (!useHls && !(!tryWebrtcFirst && hlsUrl)) return;
    if (!hlsUrl || !videoRef.current) return;
    if (Hls.isSupported()) {
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoRef.current);
      return () => {
        hls.destroy();
        hlsRef.current = null;
      };
    }
    if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = hlsUrl;
      return () => { if (videoRef.current) videoRef.current.src = ''; };
    }
  }, [useHls, hlsUrl, tryWebrtcFirst]);

  // After WebRTC error, switch to HLS
  useEffect(() => {
    if (webrtcError && hlsUrl) setUseHls(true);
  }, [webrtcError, hlsUrl]);

  const statusLabel = vpsStatus == null ? 'connecting' : (vpsStatus.status === 'live' ? 'live' : vpsStatus.status === 'connecting' ? 'connecting' : 'offline');
  const statusColor = statusLabel === 'live' ? 'green' : statusLabel === 'connecting' ? 'yellow' : 'red';

  return (
    <Box position="relative" w="full" h="full">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
      />
      <Flex position="absolute" top={2} right={2} align="center" gap={2} bg="blackAlpha.7" px={2} py={1} borderRadius="md">
        <Box w={2} h={2} borderRadius="full" bg={`${statusColor}.400`} />
        <Text fontSize="xs" color="white">{statusLabel}</Text>
      </Flex>
    </Box>
  );
}

export default function StreamPlayer({ apiBaseUrl }: { apiBaseUrl: string }) {
  const config = useStreamConfig();
  const vpsStatus = useVpsStatus(config?.stream_mode || 'local', config?.stream_mode === 'vps');

  if (!config) {
    return (
      <Flex h="full" align="center" justify="center">
        <Spinner size="lg" />
      </Flex>
    );
  }

  if (config.stream_mode === 'local') {
    const src = config.video_feed_url || `${apiBaseUrl}/video_feed`;
    return (
      <Box as="img" src={src} alt="Live camera" w="full" h="full" objectFit="contain" />
    );
  }

  return (
    <VpsPlayer
      config={config}
      vpsStatus={vpsStatus || { status: 'offline' }}
      videoFeedUrl={apiBaseUrl}
    />
  );
}
