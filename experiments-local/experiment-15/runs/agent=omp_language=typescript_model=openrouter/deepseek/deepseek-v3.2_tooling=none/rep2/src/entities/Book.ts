import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { IsNotEmpty, IsString, IsInt, Min, Max, IsOptional, IsISBN } from 'class-validator';

@Entity()
export class Book {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column()
  @IsNotEmpty({ message: 'Title is required' })
  @IsString()
  title!: string;

  @Column()
  @IsNotEmpty({ message: 'Author is required' })
  @IsString()
  author!: string;

  @Column('integer')
  @IsInt()
  @Min(1000, { message: 'Year must be at least 1000' })
  @Max(new Date().getFullYear(), { message: 'Year cannot be in the future' })
  year!: number;

  @Column({ unique: true })
  @IsNotEmpty({ message: 'ISBN is required' })
  @IsISBN()
  isbn!: string;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;
}

export class CreateBookDto {
  @IsNotEmpty({ message: 'Title is required' })
  @IsString()
  title!: string;

  @IsNotEmpty({ message: 'Author is required' })
  @IsString()
  author!: string;

  @IsInt()
  @Min(1000, { message: 'Year must be at least 1000' })
  @Max(new Date().getFullYear(), { message: 'Year cannot be in the future' })
  year!: number;

  @IsNotEmpty({ message: 'ISBN is required' })
  @IsISBN()
  isbn!: string;
}

export class UpdateBookDto {
  @IsOptional()
  @IsString()
  title?: string;

  @IsOptional()
  @IsString()
  author?: string;

  @IsOptional()
  @IsInt()
  @Min(1000, { message: 'Year must be at least 1000' })
  @Max(new Date().getFullYear(), { message: 'Year cannot be in the future' })
  year?: number;

  @IsOptional()
  @IsISBN()
  isbn?: string;
}