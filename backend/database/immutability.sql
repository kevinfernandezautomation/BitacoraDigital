-- Ejecutar después de migraciones PostgreSQL, con rol de migración separado.
CREATE OR REPLACE FUNCTION protect_sheet() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.closed THEN RAISE EXCEPTION 'Hoja cerrada'; END IF; IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW; END $$;
CREATE TRIGGER protect_sheet_trigger BEFORE UPDATE OR DELETE ON core_sheet FOR EACH ROW EXECUTE FUNCTION protect_sheet();
CREATE OR REPLACE FUNCTION protect_attachment() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP <> 'INSERT' THEN PERFORM id FROM core_sheet WHERE id=OLD.sheet_id FOR UPDATE; IF EXISTS(SELECT 1 FROM core_sheet WHERE id=OLD.sheet_id AND closed) THEN RAISE EXCEPTION 'Adjunto cerrado'; END IF; END IF; IF TG_OP <> 'DELETE' THEN PERFORM id FROM core_sheet WHERE id=NEW.sheet_id FOR UPDATE; IF EXISTS(SELECT 1 FROM core_sheet WHERE id=NEW.sheet_id AND closed) THEN RAISE EXCEPTION 'Adjunto cerrado'; END IF; RETURN NEW; END IF; RETURN OLD; END $$;
CREATE TRIGGER protect_attachment_trigger BEFORE INSERT OR UPDATE OR DELETE ON core_attachment FOR EACH ROW EXECUTE FUNCTION protect_attachment();
CREATE OR REPLACE FUNCTION protect_comment() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Comentario inalterable'; END IF; PERFORM id FROM core_sheet WHERE id=NEW.sheet_id AND closed FOR UPDATE; IF NOT FOUND THEN RAISE EXCEPTION 'Hoja no cerrada'; END IF; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS protect_comment_trigger ON core_comment;
CREATE TRIGGER protect_comment_trigger BEFORE INSERT OR UPDATE OR DELETE ON core_comment FOR EACH ROW EXECUTE FUNCTION protect_comment();
CREATE OR REPLACE FUNCTION protect_archive() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Archivo histórico inalterable'; END $$;
DROP TRIGGER IF EXISTS archive_guard ON core_closedarchive;
CREATE TRIGGER archive_guard BEFORE UPDATE OR DELETE ON core_closedarchive FOR EACH ROW EXECUTE FUNCTION protect_archive();
DROP TRIGGER IF EXISTS archived_file_guard ON core_archivedfile;
CREATE TRIGGER archived_file_guard BEFORE UPDATE OR DELETE ON core_archivedfile FOR EACH ROW EXECUTE FUNCTION protect_archive();
CREATE OR REPLACE FUNCTION guard_archive_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_TABLE_NAME='core_closedarchive' THEN PERFORM id FROM core_sheet WHERE id=NEW.sheet_id AND NOT closed FOR UPDATE;
 ELSE PERFORM s.id FROM core_sheet s JOIN core_closedarchive a ON a.sheet_id=s.id WHERE a.id=NEW.archive_id AND NOT s.closed FOR UPDATE OF s; END IF;
 IF NOT FOUND THEN RAISE EXCEPTION 'Archivo ya cerrado'; END IF; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS archive_insert_guard ON core_closedarchive;
CREATE TRIGGER archive_insert_guard BEFORE INSERT ON core_closedarchive FOR EACH ROW EXECUTE FUNCTION guard_archive_insert();
DROP TRIGGER IF EXISTS archived_file_insert_guard ON core_archivedfile;
CREATE TRIGGER archived_file_insert_guard BEFORE INSERT ON core_archivedfile FOR EACH ROW EXECUTE FUNCTION guard_archive_insert();
CREATE OR REPLACE FUNCTION guard_task() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Tarea no eliminable'; END IF;
 IF TG_OP='INSERT' THEN PERFORM id FROM core_sheet WHERE id=NEW.sheet_id AND closed FOR UPDATE; IF NOT FOUND THEN RAISE EXCEPTION 'Hoja no cerrada'; END IF;
 ELSE
 IF ROW(NEW.id,NEW.sheet_id,NEW.creator_id,NEW.assignee_id,NEW.body,NEW.due,NEW.created) IS DISTINCT FROM ROW(OLD.id,OLD.sheet_id,OLD.creator_id,OLD.assignee_id,OLD.body,OLD.due,OLD.created) THEN RAISE EXCEPTION 'Asignación inalterable'; END IF;
 IF NOT ((OLD.status='Pendiente' AND NEW.status IN ('En progreso','Realizada','Suspendida')) OR (OLD.status='En progreso' AND NEW.status IN ('Realizada','Suspendida')) OR (OLD.status='Suspendida' AND NEW.status='Pendiente')) THEN RAISE EXCEPTION 'Transición inválida'; END IF;
 END IF; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS task_guard ON core_task;
CREATE TRIGGER task_guard BEFORE INSERT OR UPDATE OR DELETE ON core_task FOR EACH ROW EXECUTE FUNCTION guard_task();
DROP TRIGGER IF EXISTS task_event_guard ON core_taskevent;
CREATE TRIGGER task_event_guard BEFORE UPDATE OR DELETE ON core_taskevent FOR EACH ROW EXECUTE FUNCTION protect_archive();
CREATE OR REPLACE FUNCTION guard_delivery() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Historial de envío no eliminable'; END IF;
 IF TG_OP='INSERT' THEN
  IF NOT EXISTS(SELECT 1 FROM core_sheet s JOIN core_regency r ON r.id=s.regency_id JOIN core_user u ON u.id=NEW.actor_id WHERE s.id=NEW.sheet_id AND s.closed AND s.digest=NEW.digest AND r.owner_id=u.id AND u.role='regente' AND u.is_active AND NOT u.suspended) OR NEW.status<>'registrado' OR NEW.finished IS NOT NULL THEN RAISE EXCEPTION 'Envío no autorizado'; END IF;
 ELSE
  IF ROW(NEW.id,NEW.sheet_id,NEW.actor_id,NEW.recipient,NEW.digest,NEW.created) IS DISTINCT FROM ROW(OLD.id,OLD.sheet_id,OLD.actor_id,OLD.recipient,OLD.digest,OLD.created) OR OLD.status<>'registrado' OR NEW.status NOT IN ('aceptado','simulado','incierto') OR NEW.finished IS NULL THEN RAISE EXCEPTION 'Historial de envío inalterable'; END IF;
 END IF; RETURN NEW; END $$;
DROP TRIGGER IF EXISTS delivery_guard ON core_delivery;
CREATE TRIGGER delivery_guard BEFORE INSERT OR UPDATE OR DELETE ON core_delivery FOR EACH ROW EXECUTE FUNCTION guard_delivery();
